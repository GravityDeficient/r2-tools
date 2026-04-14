# Changelog

Each tool in this repo versions independently. Tags follow `<tool>-vX.Y.Z` (e.g. `sync-v0.1.0`).
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### r2-sync

- Initial scaffolding.
- Core `r2_sync.py` entrypoint: pydantic v2 config, mtime + filename-date retention strategies, rclone subprocess with `--use-json-log` forwarding, structured JSON logs.
- Unit tests covering date math, rclone arg construction, config validation, and log output (49 tests, all passing).

### r2-indexer

- Not yet started.
