#!/bin/sh
set -eu

# Weather forecast R2 sync
# Syncs WRF and CBL forecast output to Cloudflare R2
# Only keeps the last 7 days of data
# Generates an index.html with links to chart PNGs

BUCKET="${R2_BUCKET:?R2_BUCKET is required}"
SOURCE_DIR="${WEATHER_ARCHIVE_DIR:-/data/weather-archive}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
INDEX_FILE="/tmp/index.html"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }

# Verify rclone config
if ! rclone listremotes | grep -q "^r2:$"; then
    log "ERROR: rclone remote 'r2' not configured"
    exit 1
fi

# Verify source exists
if [ ! -d "$SOURCE_DIR" ]; then
    log "ERROR: Source directory $SOURCE_DIR not found"
    exit 1
fi

log "Starting sync to r2:${BUCKET} (retaining ${RETAIN_DAYS} days)"

# Build include patterns for the last N days, keyed off dates embedded in
# filenames (e.g. conditions_2026-04-07.png, cbl_2026-04-07_hrrr.json).
# Filesystem mtime is NOT reliable — WRF pipeline rewrites old files — so
# we must filter by the date string in the filename itself.
INCLUDE_ARGS=""
NOW_EPOCH=$(date -u +%s)
i=0
FIRST_DATE=""
LAST_DATE=""
while [ "$i" -lt "$RETAIN_DAYS" ]; do
    d=$(date -u -d "@$((NOW_EPOCH - i * 86400))" +%Y-%m-%d)
    INCLUDE_ARGS="${INCLUDE_ARGS} --include *${d}*.json --include *${d}*.png"
    [ -z "$LAST_DATE" ] && LAST_DATE="$d"
    FIRST_DATE="$d"
    i=$((i + 1))
done
log "Including filename dates: ${FIRST_DATE} .. ${LAST_DATE}"

# Sync WRF output (last N days by filename date)
if [ -d "$SOURCE_DIR/wrf-output" ]; then
    log "Syncing WRF output..."
    # shellcheck disable=SC2086
    rclone copy "$SOURCE_DIR/wrf-output/" "r2:${BUCKET}/wrf/" \
        $INCLUDE_ARGS \
        --no-update-modtime \
        --transfers 4 \
        --checkers 8 \
        --log-level INFO
    log "WRF sync complete (retention handled by R2 lifecycle rules)"
else
    log "WARN: $SOURCE_DIR/wrf-output not found, skipping"
fi

# Sync CBL output (last N days by filename date)
if [ -d "$SOURCE_DIR/cbl-output" ]; then
    log "Syncing CBL output..."
    # shellcheck disable=SC2086
    rclone copy "$SOURCE_DIR/cbl-output/" "r2:${BUCKET}/cbl/" \
        $INCLUDE_ARGS \
        --no-update-modtime \
        --transfers 4 \
        --checkers 8 \
        --log-level INFO
    log "CBL sync complete (retention handled by R2 lifecycle rules)"
else
    log "WARN: $SOURCE_DIR/cbl-output not found, skipping"
fi

# Generate index.html from recent PNGs
log "Generating index.html..."

# Collect WRF charts from R2 (newest first) — R2 is source of truth
WRF_CHARTS=$(rclone lsjson "r2:${BUCKET}/wrf/" -R --files-only 2>/dev/null \
    | jq -r '.[] | select(.Name | endswith(".png")) | "\(.ModTime)\t\(.Path)"' \
    | sort -r | cut -f2)

# Collect CBL charts from R2 (newest first)
CBL_CHARTS=$(rclone lsjson "r2:${BUCKET}/cbl/" -R --files-only 2>/dev/null \
    | jq -r '.[] | select(.Name | endswith(".png")) | "\(.ModTime)\t\(.Path)"' \
    | sort -r | cut -f2)

UPDATED=$(date -u '+%Y-%m-%d %H:%M UTC')

cat > "$INDEX_FILE" << 'HEADER'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather Ops — Forecast Charts</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, 'Segoe UI', Roboto, monospace;
    background: #0d1117; color: #c9d1d9;
    padding: 1.5rem; max-width: 1000px; margin: 0 auto;
  }
  h1 { font-size: 1.3rem; color: #58a6ff; margin-bottom: 0.25rem; }
  .updated { color: #484f58; font-size: 0.8rem; margin-bottom: 1.5rem; }
  h2 { font-size: 1rem; color: #8b949e; margin: 1.5rem 0 0.75rem;
       border-bottom: 1px solid #21262d; padding-bottom: 0.4rem; }
  .charts { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; }
  .chart a { display: block; text-decoration: none; color: #c9d1d9;
             background: #161b22; border: 1px solid #21262d; border-radius: 6px;
             padding: 0.5rem; transition: border-color 0.2s; }
  .chart a:hover { border-color: #58a6ff; }
  .chart img { width: 100%; border-radius: 4px; }
  .chart .label { font-size: 0.8rem; padding: 0.4rem 0 0; color: #8b949e; }
  .empty { color: #484f58; font-style: italic; }
</style>
</head>
<body>
<h1>Weather Ops</h1>
HEADER

echo "<p class=\"updated\">Updated: ${UPDATED}</p>" >> "$INDEX_FILE"

# WRF section
echo '<h2>WRF 1km Forecasts</h2>' >> "$INDEX_FILE"
if [ -n "$WRF_CHARTS" ]; then
    echo '<div class="charts">' >> "$INDEX_FILE"
    echo "$WRF_CHARTS" | while read -r relpath; do
        [ -z "$relpath" ] && continue
        filename=$(basename "$relpath")
        echo "<div class=\"chart\"><a href=\"wrf/${relpath}\" target=\"_blank\"><img src=\"wrf/${relpath}\" loading=\"lazy\"><div class=\"label\">${filename}</div></a></div>" >> "$INDEX_FILE"
    done
    echo '</div>' >> "$INDEX_FILE"
else
    echo '<p class="empty">No WRF charts in the last '"${RETAIN_DAYS}"' days</p>' >> "$INDEX_FILE"
fi

# CBL section
echo '<h2>CBL Block Predictions</h2>' >> "$INDEX_FILE"
if [ -n "$CBL_CHARTS" ]; then
    echo '<div class="charts">' >> "$INDEX_FILE"
    echo "$CBL_CHARTS" | while read -r relpath; do
        [ -z "$relpath" ] && continue
        filename=$(basename "$relpath")
        echo "<div class=\"chart\"><a href=\"cbl/${relpath}\" target=\"_blank\"><img src=\"cbl/${relpath}\" loading=\"lazy\"><div class=\"label\">${filename}</div></a></div>" >> "$INDEX_FILE"
    done
    echo '</div>' >> "$INDEX_FILE"
else
    echo '<p class="empty">No CBL charts in the last '"${RETAIN_DAYS}"' days</p>' >> "$INDEX_FILE"
fi

cat >> "$INDEX_FILE" << 'FOOTER'
</body>
</html>
FOOTER

# Upload index.html
rclone copyto "$INDEX_FILE" "r2:${BUCKET}/index.html" --log-level INFO
rm -f "$INDEX_FILE"
log "Index uploaded"

log "All syncs complete"
