# r2-tools

A small collection of Cloudflare R2 utilities that ship as independent container images from one repo.

## Tools

### [r2-sync](sync/)

Push local directories to R2 with configurable retention (mtime default, filename-date opt-in). Thin wrapper around `rclone` that fills the specific gap of filename-embedded-date retention, which the rclone ecosystem doesn't ship.

- Image: `ghcr.io/gravitydeficient/r2-sync` (multi-arch: amd64 + arm64)
- Docs: [`sync/README.md`](sync/README.md)
- Examples: [`examples/compose/`](examples/compose/), [`examples/k3s/`](examples/k3s/)

### r2-indexer *(planned)*

Run directly against R2 (no local mount) to generate a browseable `index.html` of synced objects. Decoupled from r2-sync; independent schedule; different failure surface. Not yet started.

## Quickstart

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

See [`sync/README.md`](sync/README.md) for the config reference and full deployment examples.

## Versioning

Each tool releases independently under its own semver tag prefix:

- `sync-v0.1.0`, `sync-v0.1.1`, ... → image `ghcr.io/gravitydeficient/r2-sync:v0.1.0` (and `:v0.1`, `:v0`)
- `indexer-v0.1.0`, ... → image `ghcr.io/gravitydeficient/r2-indexer:v0.1.0` (when the tool ships)

See [`CHANGELOG.md`](CHANGELOG.md) for release history.

## License

[MIT](LICENSE).
