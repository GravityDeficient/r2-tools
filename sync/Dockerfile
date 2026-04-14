# syntax=docker/dockerfile:1.7
FROM python:3.12-alpine

# rclone: pinned for reproducibility. Bump in a single commit, noted in
# CHANGELOG.md, and accept any Alpine repo drift as a deliberate upgrade.
RUN apk add --no-cache rclone=1.72.1-r3

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY r2_sync.py ./

USER 1000
ENV R2_SYNC_CONFIG=/config/r2-sync.yml

ENTRYPOINT ["python", "/app/r2_sync.py"]
