#!/usr/bin/env python3
"""Push a local directory to a Cloudflare R2 prefix with configurable retention.

Thin wrapper around rclone. Two retention strategies:
    - mtime (default): rclone --max-age N days
    - filename-date:   build an explicit include list as the cartesian
                       product of patterns x YYYY-MM-DD dates in the window.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


# ---------------------------------------------------------------------------
# Config schema
# ---------------------------------------------------------------------------

class RetentionStrategy(str, Enum):
    MTIME = "mtime"
    FILENAME_DATE = "filename-date"


class R2Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bucket: str


class Retention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: RetentionStrategy = RetentionStrategy.MTIME
    days: int = Field(gt=0)


class RcloneExtras(BaseModel):
    # Unknown keys pass through to rclone as CLI flags (see _extras_to_args).
    model_config = ConfigDict(extra="allow")
    transfers: int = 4
    checkers: int = 8


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    r2: R2Settings
    source: str
    prefix: str
    patterns: list[str] = Field(min_length=1)
    retention: Retention
    rclone: RcloneExtras = Field(default_factory=RcloneExtras)


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_CONFIG_NOT_FOUND = 1
EXIT_CONFIG_INVALID = 2
EXIT_RCLONE_NOT_FOUND = 3


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable)
# ---------------------------------------------------------------------------

def dates_in_window(days: int, now: dt.date | None = None) -> list[str]:
    """Return the last `days` UTC dates as YYYY-MM-DD strings, today first."""
    if days <= 0:
        raise ValueError("days must be > 0")
    if now is None:
        now = dt.datetime.now(dt.timezone.utc).date()
    return [(now - dt.timedelta(days=i)).isoformat() for i in range(days)]


def _filename_date_include(pattern: str, date: str) -> str:
    """Build a rclone --include glob that matches `pattern` AND contains `date`."""
    if pattern.startswith("*"):
        return f"*{date}*{pattern[1:]}"
    return f"*{date}*{pattern}"


def _extras_to_args(extras: RcloneExtras) -> list[str]:
    """Translate RcloneExtras to rclone CLI flags (see ASI §5.2.4)."""
    args: list[str] = []
    for key, value in extras.model_dump().items():
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                args.append(flag)
        elif isinstance(value, (int, float)):
            args.extend([flag, str(value)])
        elif isinstance(value, str):
            args.extend([flag, value])
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, str):
                    raise ValueError(
                        f"rclone extras: list for {key!r} must contain strings"
                    )
                args.extend([flag, item])
        elif value is None:
            raise ValueError(f"rclone extras: value for {key!r} cannot be None")
        else:
            raise ValueError(
                f"rclone extras: unsupported type {type(value).__name__} for {key!r}"
            )
    return args


def build_rclone_args(
    config: Config,
    dry_run: bool,
    now: dt.date | None = None,
) -> list[str]:
    """Translate Config to argv for the rclone subprocess."""
    args: list[str] = [
        "rclone",
        "copy",
        config.source,
        f"r2:{config.r2.bucket}/{config.prefix}",
        "--no-update-modtime",
        "--use-json-log",
        "--stats", "0",
        "--stats-log-level", "NOTICE",
    ]

    if config.retention.strategy is RetentionStrategy.MTIME:
        args.extend(["--max-age", f"{config.retention.days}d"])
        for pattern in config.patterns:
            args.extend(["--include", pattern])
    else:  # FILENAME_DATE
        for date in dates_in_window(config.retention.days, now=now):
            for pattern in config.patterns:
                args.extend(["--include", _filename_date_include(pattern, date)])

    args.extend(_extras_to_args(config.rclone))

    if dry_run:
        args.append("--dry-run")

    return args


_TRANSFERRED_RE = re.compile(r"Transferred:\s+(\d+)\s*/\s*(\d+)")


def parse_rclone_transfers(msg: str) -> int | None:
    """Extract the file count from a rclone stats log message.

    rclone's stats block has two "Transferred:" lines — one for bytes (with
    units like "1.2 GiB / 1.2 GiB") and one for files (pure integers "10 / 10").
    The regex matches only the integer form, so we return the last match.
    Returns None if no integer Transferred: line is present.
    """
    matches = _TRANSFERRED_RE.findall(msg)
    if not matches:
        return None
    return int(matches[-1][0])


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> Config:
    """Read YAML at `path`, validate, return typed Config."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)


def _now_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def emit_log(event: str, **fields: Any) -> None:
    """Emit a single JSON line to stdout tagged as r2-sync."""
    payload: dict[str, Any] = {
        "time": _now_iso(),
        "source": "r2-sync",
        "event": event,
        **fields,
    }
    print(json.dumps(payload, default=str), flush=True)


def build_rclone_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Bridge R2_* env vars to rclone's RCLONE_CONFIG_R2_* convention."""
    env = dict(base_env if base_env is not None else os.environ)
    bridges = {
        "R2_ACCESS_KEY_ID": "RCLONE_CONFIG_R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY": "RCLONE_CONFIG_R2_SECRET_ACCESS_KEY",
        "R2_ENDPOINT": "RCLONE_CONFIG_R2_ENDPOINT",
    }
    for src, dst in bridges.items():
        if src in env and dst not in env:
            env[dst] = env[src]
    env.setdefault("RCLONE_CONFIG_R2_TYPE", "s3")
    env.setdefault("RCLONE_CONFIG_R2_PROVIDER", "Cloudflare")
    return env


def run_rclone(args: list[str], env: dict[str, str] | None = None) -> tuple[int, int | None]:
    """Run rclone, forwarding its JSON log lines with a `source: rclone` tag.

    Returns (exit_code, files_transferred). files_transferred is None if the
    count couldn't be parsed from rclone's stats output.
    """
    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    files_transferred: int | None = None
    assert proc.stderr is not None
    for raw in proc.stderr:
        line = raw.rstrip("\n")
        if not line:
            continue
        try:
            obj = json.loads(line)
            obj["source"] = "rclone"
            msg = obj.get("msg", "")
            if isinstance(msg, str) and "Transferred:" in msg:
                count = parse_rclone_transfers(msg)
                if count is not None:
                    files_transferred = count
            print(json.dumps(obj, default=str), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({"source": "rclone", "raw": line}), flush=True)

    proc.wait()
    return proc.returncode, files_transferred


def _env_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config_path = os.environ.get("R2_SYNC_CONFIG", "/config/r2-sync.yml")
    dry_run = _env_truthy(os.environ.get("R2_SYNC_DRYRUN")) or "--dry-run" in argv

    if not os.path.exists(config_path):
        emit_log("error", error="config_not_found", path=config_path)
        return EXIT_CONFIG_NOT_FOUND

    try:
        config = load_config(config_path)
    except (ValidationError, yaml.YAMLError) as e:
        emit_log("error", error="config_invalid", path=config_path, detail=str(e))
        return EXIT_CONFIG_INVALID

    if shutil.which("rclone") is None:
        emit_log("error", error="rclone_not_found")
        return EXIT_RCLONE_NOT_FOUND

    if not os.path.isdir(config.source):
        # Empty/missing source dir: warn and let rclone produce a clear error
        # (or exit 0 with 0 transfers if the parent exists).
        emit_log("warning", warning="source_not_a_directory", source=config.source)

    emit_log(
        "start",
        config=config_path,
        bucket=config.r2.bucket,
        prefix=config.prefix,
        strategy=config.retention.strategy.value,
        days=config.retention.days,
        dry_run=dry_run,
    )

    started_at = dt.datetime.now(dt.timezone.utc)
    args = build_rclone_args(config, dry_run=dry_run)
    exit_code, files_transferred = run_rclone(args, env=build_rclone_env())
    duration = (dt.datetime.now(dt.timezone.utc) - started_at).total_seconds()

    emit_log(
        "complete",
        exit_code=exit_code,
        files_transferred=files_transferred,
        duration_seconds=round(duration, 2),
        dry_run=dry_run,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
