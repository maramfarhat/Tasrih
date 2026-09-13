#!/usr/bin/env bash
# Lance l'API Tasrih (FastAPI) sur http://127.0.0.1:8010
set -euo pipefail
cd "$(dirname "$0")/backend"

if [ ! -d .venv ]; then
  echo "[tasrih] création de l'environnement virtuel…"
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt
fi

export PYTHONPATH="$PWD"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
