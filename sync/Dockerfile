# syntax=docker/dockerfile:1.7
FROM python:3.12-alpine

# rclone: unpinned during early development. At v0.1.0 cut, pin to the
# resolved version (e.g. rclone=1.70.2-r0) for reproducibility and track
# bumps in CHANGELOG.md.
RUN apk add --no-cache rclone

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY r2_sync.py ./

USER 1000
ENV R2_SYNC_CONFIG=/config/r2-sync.yml

ENTRYPOINT ["python", "/app/r2_sync.py"]
