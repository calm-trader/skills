#!/usr/bin/env bash
# Copy the fixture target into a fresh git repository the reader can be pointed at.
# The answer key stays here. Prints the sandbox path.
#
#   ./make-sandbox.sh [dir]     default: a new temporary directory
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/target"
DST="${1:-$(mktemp -d -t falsify-fixture-XXXXXX)}"
mkdir -p "$DST"
cp -R "$SRC"/. "$DST"/
rm -rf "$DST"/ledger/__pycache__ "$DST"/tests/__pycache__
( cd "$DST" && git init -q && git add -A && git -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "ledger" )
echo "$DST"
