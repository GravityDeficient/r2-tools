import io
import json
from contextlib import redirect_stdout

from r2_sync import emit_log, parse_rclone_transfers


# -- emit_log ---------------------------------------------------------------

def _captured(emit_fn) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        emit_fn()
    return buf.getvalue()


def test_emit_log_is_json_with_source_tag():
    output = _captured(lambda: emit_log("start", config="/x"))
    obj = json.loads(output.strip())
    assert obj["source"] == "r2-sync"
    assert obj["event"] == "start"
    assert obj["config"] == "/x"
    assert "time" in obj


def test_emit_log_timestamp_uses_z_suffix():
    output = _captured(lambda: emit_log("ping"))
    obj = json.loads(output.strip())
    assert obj["time"].endswith("Z")


def test_emit_log_is_single_line():
    output = _captured(lambda: emit_log("complete", exit_code=0, files_transferred=3))
    assert output.count("\n") == 1
    obj = json.loads(output.strip())
    assert obj["exit_code"] == 0
    assert obj["files_transferred"] == 3


def test_emit_log_preserves_collection_values():
    output = _captured(lambda: emit_log("info", items=["a", "b"], counts={"ok": 5}))
    obj = json.loads(output.strip())
    assert obj["items"] == ["a", "b"]
    assert obj["counts"] == {"ok": 5}


def test_emit_log_event_name_survives():
    output = _captured(lambda: emit_log("complete"))
    assert json.loads(output.strip())["event"] == "complete"


# -- parse_rclone_transfers -------------------------------------------------

def test_parse_rclone_transfers_typical_stats_block():
    # rclone --use-json-log + --stats emits a multi-line stats msg. The first
    # "Transferred:" line is bytes, the second is files. We extract the second.
    msg = (
        "\nTransferred:   \t          1.234 GiB / 1.234 GiB, 100%, 0 B/s, ETA -\n"
        "Transferred:            10 / 10, 100%\n"
        "Errors:                 0\n"
        "Checks:                 0 / 0, -\n"
        "Elapsed time:           5.0s\n"
    )
    assert parse_rclone_transfers(msg) == 10


def test_parse_rclone_transfers_zero_files():
    msg = (
        "\nTransferred:   \t          0 B / 0 B, -\n"
        "Transferred:            0 / 0, -\n"
    )
    assert parse_rclone_transfers(msg) == 0


def test_parse_rclone_transfers_no_match_returns_none():
    assert parse_rclone_transfers("some unrelated log line") is None


def test_parse_rclone_transfers_bytes_only_returns_none():
    # A bytes-only line (units like "1.2 GiB") doesn't match the integer regex.
    # No integer match -> None (we don't know the file count, don't lie).
    msg = "\nTransferred: 1.2 GiB / 1.2 GiB, 100%\n"
    assert parse_rclone_transfers(msg) is None
