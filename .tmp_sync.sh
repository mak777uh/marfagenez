#!/bin/bash
set -e
SRC=/root/marfagenez/laws/Medium
DST=/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/marfagenez/laws/Medium
for f in Field.lean Feed.lean Capacity.lean Convergence.lean Regimes.lean Medium.lean CapacityLaw.lean; do
  if [ -f "$SRC/$f" ]; then cp "$SRC/$f" "$DST/$f"; echo "synced $f"; fi
done
