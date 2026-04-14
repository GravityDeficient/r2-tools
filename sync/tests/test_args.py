import datetime as dt

from r2_sync import (
    Config,
    R2Settings,
    RcloneExtras,
    Retention,
    RetentionStrategy,
    _filename_date_include,
    build_rclone_args,
)


def make_config(**overrides) -> Config:
    base = dict(
        r2=R2Settings(bucket="test-bucket"),
        source="/data",
        prefix="wrf",
        patterns=["*.json", "*.png"],
        retention=Retention(strategy=RetentionStrategy.MTIME, days=7),
    )
    base.update(overrides)
    return Config(**base)


def _includes(args: list[str]) -> list[str]:
    return [args[i + 1] for i, a in enumerate(args) if a == "--include"]


# -- Structure --------------------------------------------------------------

def test_first_four_args_are_copy_source_dest():
    args = build_rclone_args(make_config(), dry_run=False)
    assert args[0] == "rclone"
    assert args[1] == "copy"
    assert args[2] == "/data"
    assert args[3] == "r2:test-bucket/wrf"


def test_prefix_composed_correctly():
    args = build_rclone_args(make_config(prefix="cbl"), dry_run=False)
    assert args[3] == "r2:test-bucket/cbl"


# -- Always-present flags ---------------------------------------------------

def test_no_update_modtime_always_present():
    args = build_rclone_args(make_config(), dry_run=False)
    assert "--no-update-modtime" in args


def test_use_json_log_always_present():
    args = build_rclone_args(make_config(), dry_run=False)
    assert "--use-json-log" in args


def test_stats_configured_for_end_of_run_summary():
    args = build_rclone_args(make_config(), dry_run=False)
    assert "--stats" in args
    assert args[args.index("--stats") + 1] == "0"
    assert "--stats-log-level" in args


# -- mtime strategy ---------------------------------------------------------

def test_mtime_has_max_age_matching_retention_days():
    args = build_rclone_args(make_config(), dry_run=False)
    assert args[args.index("--max-age") + 1] == "7d"


def test_mtime_emits_raw_pattern_includes():
    args = build_rclone_args(make_config(), dry_run=False)
    assert "*.json" in _includes(args)
    assert "*.png" in _includes(args)


def test_mtime_strategy_days_varies():
    cfg = make_config(retention=Retention(strategy=RetentionStrategy.MTIME, days=14))
    args = build_rclone_args(cfg, dry_run=False)
    assert args[args.index("--max-age") + 1] == "14d"


# -- filename-date strategy -------------------------------------------------

def test_filename_date_cartesian_product():
    cfg = make_config(
        retention=Retention(strategy=RetentionStrategy.FILENAME_DATE, days=2),
        patterns=["*.json", "*.png"],
    )
    args = build_rclone_args(cfg, dry_run=False, now=dt.date(2026, 4, 13))
    includes = _includes(args)
    assert len(includes) == 4  # 2 days x 2 patterns
    assert "*2026-04-13*.json" in includes
    assert "*2026-04-13*.png" in includes
    assert "*2026-04-12*.json" in includes
    assert "*2026-04-12*.png" in includes


def test_filename_date_no_max_age():
    cfg = make_config(
        retention=Retention(strategy=RetentionStrategy.FILENAME_DATE, days=3),
    )
    args = build_rclone_args(cfg, dry_run=False)
    assert "--max-age" not in args


def test_filename_date_include_transform():
    assert _filename_date_include("*.json", "2026-04-13") == "*2026-04-13*.json"
    assert _filename_date_include("*.png", "2026-04-13") == "*2026-04-13*.png"
    assert _filename_date_include("foo.bar", "2026-04-13") == "*2026-04-13*foo.bar"
    assert _filename_date_include("data-*.csv", "2026-04-13") == "*2026-04-13*data-*.csv"


# -- dry-run ----------------------------------------------------------------

def test_dry_run_appended():
    args = build_rclone_args(make_config(), dry_run=True)
    assert "--dry-run" in args


def test_dry_run_omitted_when_false():
    args = build_rclone_args(make_config(), dry_run=False)
    assert "--dry-run" not in args


# -- rclone extras pass-through (§5.2.4) -----------------------------------

def test_defaults_transfers_and_checkers_present():
    args = build_rclone_args(make_config(), dry_run=False)
    assert args[args.index("--transfers") + 1] == "4"
    assert args[args.index("--checkers") + 1] == "8"


def test_extras_int_override():
    cfg = make_config(rclone=RcloneExtras(transfers=8))
    args = build_rclone_args(cfg, dry_run=False)
    assert args[args.index("--transfers") + 1] == "8"


def test_extras_str_passthrough():
    cfg = make_config(rclone=RcloneExtras(bwlimit="10M"))
    args = build_rclone_args(cfg, dry_run=False)
    assert args[args.index("--bwlimit") + 1] == "10M"


def test_extras_bool_true_emits_bare_flag():
    cfg = make_config(rclone=RcloneExtras(use_server_modtime=True))
    args = build_rclone_args(cfg, dry_run=False)
    assert "--use-server-modtime" in args
    idx = args.index("--use-server-modtime")
    # next token must be another flag or end-of-args — not a value
    if idx + 1 < len(args):
        assert args[idx + 1].startswith("--") or args[idx + 1] == "--dry-run"


def test_extras_bool_false_omitted_entirely():
    cfg = make_config(rclone=RcloneExtras(use_server_modtime=False))
    args = build_rclone_args(cfg, dry_run=False)
    assert "--use-server-modtime" not in args
    assert "--no-use-server-modtime" not in args


def test_extras_list_repeats_flag():
    cfg = make_config(rclone=RcloneExtras(exclude=["*.tmp", "*.log"]))
    args = build_rclone_args(cfg, dry_run=False)
    values = [args[i + 1] for i, a in enumerate(args) if a == "--exclude"]
    assert values == ["*.tmp", "*.log"]


def test_underscore_to_dash_in_flag_name():
    cfg = make_config(rclone=RcloneExtras(use_server_modtime=True))
    args = build_rclone_args(cfg, dry_run=False)
    assert "--use-server-modtime" in args
    assert "--use_server_modtime" not in args
