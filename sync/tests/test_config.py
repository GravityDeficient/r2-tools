import pytest
from pydantic import ValidationError

from r2_sync import Config


def _valid_minimal() -> dict:
    return {
        "r2": {"bucket": "b"},
        "source": "/data",
        "prefix": "p",
        "patterns": ["*.json"],
        "retention": {"days": 7},
    }


def test_valid_minimal_config_loads():
    cfg = Config.model_validate(_valid_minimal())
    assert cfg.r2.bucket == "b"
    assert cfg.retention.strategy.value == "mtime"  # default
    assert cfg.retention.days == 7
    assert cfg.rclone.transfers == 4  # default
    assert cfg.rclone.checkers == 8  # default


def test_missing_bucket_rejected():
    raw = _valid_minimal()
    raw["r2"] = {}
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_unknown_top_level_key_rejected():
    raw = _valid_minimal()
    raw["bogus"] = "nope"
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_unknown_r2_key_rejected():
    raw = _valid_minimal()
    raw["r2"]["bogus"] = 1
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_unknown_retention_key_rejected():
    raw = _valid_minimal()
    raw["retention"]["bogus"] = 1
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_empty_patterns_rejected():
    raw = _valid_minimal()
    raw["patterns"] = []
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_bad_strategy_enum_rejected():
    raw = _valid_minimal()
    raw["retention"]["strategy"] = "bogus"
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_filename_date_strategy_accepted():
    raw = _valid_minimal()
    raw["retention"]["strategy"] = "filename-date"
    cfg = Config.model_validate(raw)
    assert cfg.retention.strategy.value == "filename-date"


def test_days_must_be_positive():
    raw = _valid_minimal()
    raw["retention"]["days"] = 0
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_rclone_extras_allowed_and_accessible():
    raw = _valid_minimal()
    raw["rclone"] = {"transfers": 8, "bwlimit": "10M"}
    cfg = Config.model_validate(raw)
    dumped = cfg.rclone.model_dump()
    assert dumped["transfers"] == 8
    assert dumped["bwlimit"] == "10M"


def test_source_required():
    raw = _valid_minimal()
    del raw["source"]
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_prefix_required():
    raw = _valid_minimal()
    del raw["prefix"]
    with pytest.raises(ValidationError):
        Config.model_validate(raw)
