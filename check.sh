#!/usr/bin/env bash
# Everything CI checks, in the order it checks it. Run it before you push.
# Usage: ./check.sh
set -euo pipefail
cd "$(dirname "$0")"
RUFF_VERSION="0.17.1"
TOOLS=(open_doors stranger_test draw_table)

ruff_pinned() {
  if command -v ruff >/dev/null && [ "$(ruff --version)" = "ruff $RUFF_VERSION" ]; then
    ruff "$@"
  else
    pipx run "ruff==$RUFF_VERSION" "$@"
  fi
}

echo "== lint floor (ruff $RUFF_VERSION: lint, complexity, nesting)"
ruff_pinned check .
echo "== format"
ruff_pinned format --check .
for TOOL in "${TOOLS[@]}"; do
  echo "== tests: $TOOL"
  python3 -m unittest discover --buffer --start-directory "$TOOL" --pattern 'test_*.py'
done
echo "== the table matches the entries"
python3 draw_table/draw_table.py --check
echo "all checks passed"
