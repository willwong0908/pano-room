#!/bin/sh
set -eu
if ! command -v python3 >/dev/null || ! command -v ffmpeg >/dev/null; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 ffmpeg ca-certificates
  rm -rf /var/lib/apt/lists/*
fi
exec python3 /app/server.py
