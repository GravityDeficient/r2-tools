# r2-sync

Push local directories to a Cloudflare R2 prefix on a schedule. One container, one sync target. Configurable retention: `mtime` (thin `rclone --max-age` wrapper, default) or `filename-date` (matches `YYYY-MM-DD` in filenames — useful for pipelines where file mtime represents processing time, not content time).

Full quickstart, config reference, and deployment examples will land here in v0.1.0.

See the top-level [repo README](../README.md) for the broader `r2-tools` context.
