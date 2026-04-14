# r2-sync

Push a local directory to a Cloudflare R2 prefix on a schedule. One container, one sync target. Thin wrapper around `rclone`.

## Why this exists

`rclone` already handles the actual transfer, mtime filtering (`--max-age`), and S3/R2 protocol. It doesn't have one thing: **filename-embedded-date retention** — "keep the last N days of files whose names contain a `YYYY-MM-DD` date string." That's useful for pipelines that overwrite or rewrite files in place (weather forecasts, log rotations, data reprocessing runs) where filesystem mtime represents *processing* time, not *content* time.

r2-sync fills that gap and nothing else. If plain rclone works for you, use plain rclone.

## Quickstart

Pull the image:

```
docker pull ghcr.io/gravitydeficient/r2-sync:latest
```

Write `r2-sync.yml`:

```yaml
r2:
  bucket: your-bucket
source: /data
prefix: archive
patterns:
  - "*.json"
  - "*.png"
retention:
  strategy: filename-date    # or "mtime" (default)
  days: 7
```

Run it (dry-run first to preview the rclone command without transferring):

```
docker run --rm \
  -e R2_ACCESS_KEY_ID=... \
  -e R2_SECRET_ACCESS_KEY=... \
  -e R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com \
  -e R2_SYNC_DRYRUN=1 \
  -v $PWD/r2-sync.yml:/config/r2-sync.yml:ro \
  -v /path/to/your/source:/data:ro \
  ghcr.io/gravitydeficient/r2-sync:latest
```

Remove `R2_SYNC_DRYRUN=1` to sync for real. Schedule it via cron (or K8s CronJob — see below) for repeated runs.

## Config reference

```yaml
r2:
  bucket: string                 # required. R2 bucket name
source: string                   # required. Absolute path inside the container
prefix: string                   # required. R2 path prefix (no leading slash)
patterns:                        # required. Non-empty list of rclone glob patterns
  - "*.json"
  - "*.png"
retention:
  strategy: mtime                # mtime (default) | filename-date
  days: integer                  # required. Retention window, > 0
rclone:                          # optional. Extras pass through to rclone.
  transfers: 4                   # default 4
  checkers: 8                    # default 8
  # Any additional key becomes --<key-with-dashes> <value>:
  # bwlimit: "10M"               -> --bwlimit 10M
  # use_server_modtime: true     -> --use-server-modtime
  # exclude: ["*.tmp", "*.log"]  -> --exclude *.tmp --exclude *.log
```

### Retention strategies

| Strategy | What it does | When to use |
|----------|--------------|-------------|
| `mtime` | Wraps `rclone --max-age Nd` plus your patterns as `--include` | When file mtime reliably reflects "this file is new". Default. |
| `filename-date` | Builds an explicit include list: the cartesian product of each pattern × each date in the window, e.g. `--include *2026-04-14*.json --include *2026-04-13*.json ...` | When your pipeline rewrites files in place (forecast refresh, data backfill) and mtime no longer reflects content date |

Only `YYYY-MM-DD` date format is supported for filename-date. Dates are computed in UTC.

### Environment variables

| Var | Purpose |
|-----|---------|
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT` | R2 credentials. Required. |
| `R2_SYNC_CONFIG` | Path to the YAML config inside the container. Default: `/config/r2-sync.yml` |
| `R2_SYNC_DRYRUN` | Set to `1`/`true` to enable `rclone --dry-run` |
| `LOG_LEVEL` | Wrapper log level. Default: `INFO` |

Credentials go via environment variables — **never** in the YAML config.

## Logging

Stdout is a single JSON-per-line stream. Each line is a complete JSON object with a `source` field (`r2-sync` for wrapper events, `rclone` for rclone's own log lines). Designed for `jq`, `kubectl logs`, Loki, `docker logs`. No interleaved plaintext.

## Deployment examples

- **Docker / docker-compose**: see [`../examples/compose/`](../examples/compose/) for a template compose file, sample config, and cron invocation.
- **Kubernetes (K3s)**: see [`../examples/k3s/`](../examples/k3s/) for a full manifest set (Namespace, NFS PV, PVC, ConfigMap, Secret stub, CronJob). All values are placeholders — copy and fill in your specifics.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Sync succeeded (including empty source dir) |
| `1` | Config file not found |
| `2` | Config validation failed |
| `3` | `rclone` binary not found in the image |
| `≥4` | rclone's own non-zero exit passes through |

## Comparison with plain rclone

| Feature | `rclone copy` | `r2-sync` |
|---------|---------------|-----------|
| Multi-arch Docker image | Via community builds | Official (amd64 + arm64) |
| mtime-based retention | `--max-age Nd` | `strategy: mtime, days: N` |
| Filename-embedded-date retention | Not supported | `strategy: filename-date` |
| YAML-driven config | No (CLI flags or `rclone.conf`) | Yes |
| R2 env-var credential bridge | Manual (set `RCLONE_CONFIG_R2_*`) | Automatic from `R2_*` vars |
| Structured JSON logs | `--use-json-log` | Same, plus wrapper summary events |

## License

MIT. See [`../LICENSE`](../LICENSE).
