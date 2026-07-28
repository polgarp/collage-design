#!/usr/bin/env bash
# check_batch.sh — assert that parallel Stage A is byte-identical to serial Stage A.
#
# The whole case for --jobs rests on results not depending on scheduling order, which holds
# because every item's seed is fixed in the manifest before any work starts and nothing is
# shared between items. That is a claim about the code, so it gets a test rather than a
# comment: this builds a manifest over generated fixtures, runs it at --jobs 1 and --jobs 8,
# and diffs every output byte for byte.
#
# Usage:  scripts/check_batch.sh [N_FRAGMENTS]
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
n="${1:-12}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

python3 - "$tmp" "$n" <<'PY'
import sys, numpy as np
from PIL import Image
d, n = sys.argv[1], int(sys.argv[2])
rng = np.random.default_rng(0)
for i in range(n):
    a = rng.integers(0, 255, (120 + i * 7, 90 + i * 5, 3), dtype=np.uint8)
    Image.fromarray(a).save(f"{d}/src{i:03d}.png")
PY

for tool in cut treat; do
  for jobs in 1 8; do
    : > "$tmp/$tool.$jobs.manifest"
    for i in $(seq 0 $((n - 1))); do
      # printf, not `seq -w`: seq pads only to the width of its largest value, so a manifest
      # built that way silently references the wrong filenames for n < 10.
      p="$(printf '%03d' "$i")"
      # a per-item seed, so a scheduling-order bug would show as a swapped result
      echo "$tmp/src$p.png $tmp/out.$tool.$jobs.$p.png --seed $((i + 3))" \
        >> "$tmp/$tool.$jobs.manifest"
    done
  done
done

echo "== cut.py"
"$here/cut.py"   --style torn --jobs 1 --manifest "$tmp/cut.1.manifest"
"$here/cut.py"   --style torn --jobs 8 --manifest "$tmp/cut.8.manifest"
echo "== treat.py"
"$here/treat.py" --style duotone --jobs 1 --manifest "$tmp/treat.1.manifest"
"$here/treat.py" --style duotone --jobs 8 --manifest "$tmp/treat.8.manifest"

fail=0
for tool in cut treat; do
  for f in "$tmp/out.$tool.1."*.png; do
    b="${f/.1./.8.}"
    if ! cmp -s "$f" "$b"; then
      echo "MISMATCH: $(basename "$f") differs between --jobs 1 and --jobs 8" >&2
      fail=1
    fi
  done
done

if [ "$fail" -eq 0 ]; then
  echo "PASS — $((n * 2)) outputs byte-identical at --jobs 1 and --jobs 8"
else
  echo "FAIL — parallel output depends on scheduling order" >&2
fi
exit "$fail"
