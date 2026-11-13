#!/bin/bash
set -e
SRC=/root/marfagenez
DST=/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/marfagenez
for f in laws/Medium/Field.lean laws/Medium/Convergence.lean laws/Medium/Capacity.lean laws/Medium/Regimes.lean; do
  cp "$SRC/$f" "$DST/$f"
  echo "copied $f"
done
