#!/usr/bin/env bash
# Télécharge la voix Piper française (homme) utilisée par l'assistant.
# Le modèle (~63 Mo) n'est pas versionné : exécuter une fois après le clone.
set -euo pipefail
cd "$(dirname "$0")/backend"
mkdir -p data/tts

BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/tom/medium"
DEST="data/tts/fr_FR-tom-medium"

if [ -f "${DEST}.onnx" ]; then
  echo "[tasrih] voix déjà présente : ${DEST}.onnx"
  exit 0
fi

echo "[tasrih] téléchargement de la voix ${DEST##*/}…"
curl -fL --progress-bar -o "${DEST}.onnx" "${BASE}/fr_FR-tom-medium.onnx"
curl -fL --progress-bar -o "${DEST}.onnx.json" "${BASE}/fr_FR-tom-medium.onnx.json"
echo "[tasrih] voix prête : ${DEST}.onnx"
