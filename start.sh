#!/usr/bin/env bash
# Démarre backend + frontend Tasrih, arrête les deux ensemble.
set -euo pipefail
cd "$(dirname "$0")"
./start-backend.sh &
BACK=$!
./start-frontend.sh &
FRONT=$!
trap 'kill $BACK $FRONT 2>/dev/null || true' EXIT INT TERM
wait
