# r2-tools

A small collection of Cloudflare R2 utilities that ship as independent container images from one repo.

## Tools

- **[r2-sync](sync/)** — push local directories to R2 with configurable retention (mtime default, filename-date opt-in). Thin wrapper around `rclone` that fills the specific gap of filename-embedded-date retention, which the rclone ecosystem doesn't ship.
- **r2-indexer** *(planned)* — run directly against R2 to generate a browseable `index.html` of synced objects. Decoupled from r2-sync; no local mount needed.

Each tool has its own subdirectory, Dockerfile, README, and semver tags (`sync-v0.1.0`, `indexer-v0.1.0`).

## License

MIT. See [LICENSE](LICENSE).
