#!/usr/bin/env bash
# mux.sh — lay the code-made score under a silent master
set -euo pipefail
cd "$(dirname "$0")/.."
for f in "$@"; do
  base="out/${f}"
  [ -f "${base}.mp4" ] || { echo "missing ${base}.mp4"; exit 1; }
  ffmpeg -y -loglevel error -i "${base}.mp4" -i out/score.wav \
    -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ar 48000 -ac 2 \
    -shortest -movflags +faststart "${base}_scored.mp4"
  echo "wrote ${base}_scored.mp4"
done
