# Changelog

Each tool in this repo versions independently. Tags follow `<tool>-vX.Y.Z` (e.g. `sync-v0.1.0`).
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### r2-sync

- *(nothing yet)*

### r2-indexer

- Not yet started.

## [sync-v0.1.0] - 2026-04-14

### r2-sync

- Initial release.
- Single-file Python entrypoint wrapping `rclone`. Configurable retention: `mtime` (default, uses `rclone --max-age`) or `filename-date` (matches `YYYY-MM-DD` in filenames; explicit include-list cartesian product of patterns × dates).
- pydantic v2 config validation with strict extras on top-level keys and pass-through on the `rclone` block.
- Structured JSON logs — wrapper events tagged `source: "r2-sync"`, rclone's own `--use-json-log` output forwarded with `source: "rclone"` injected. Single JSON-per-line stream for `jq` / Loki / `kubectl logs`.
- Exit codes distinguish config-missing (1), config-invalid (2), rclone-missing (3), and pass rclone's own failures through (≥4).
- Dry-run mode via `R2_SYNC_DRYRUN=1` or `--dry-run`.
- 49 unit tests covering date math, rclone arg construction, config validation, and log format.
- Multi-arch image (amd64 + arm64) from `python:3.12-alpine` + `rclone=1.72.1-r3`.
- Deployment examples for Docker / docker-compose (with host cron) and Kubernetes (with NFS PV).
