#!/usr/bin/env bash
# Run every self-check in the repo. Needs bash, python3 and node; changes nothing.
# CI runs exactly this, so a green run here means a green run there.
set -euo pipefail
cd "$(dirname "$0")"
bash falsify/scripts/selftest.sh
bash tradingview-backtesting/scripts/selftest.sh
python3 -m unittest discover -s auto-evolve-agentic-system/scripts -p "test_*.py"
./check-falsify.sh
./check-verifier.sh
echo "all checks passed"
