#!/usr/bin/env bash
# Lance le front Tasrih (Vite) sur http://localhost:5180
set -euo pipefail
cd "$(dirname "$0")/frontend"

if [ ! -d node_modules ]; then
  npm install
fi

exec npm run dev
