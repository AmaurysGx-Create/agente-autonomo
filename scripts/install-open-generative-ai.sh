#!/usr/bin/env bash
# Instala Open-Generative-AI (estudio de imagen, video, lip sync y cinema) en ./tools/open-generative-ai
set -euo pipefail
DEST="${1:-tools/open-generative-ai}"
if [ ! -d "$DEST/.git" ]; then
  git clone --depth 1 https://github.com/Anil-matcha/Open-Generative-AI.git "$DEST"
fi
cd "$DEST"
git submodule update --init --recursive --depth 1
npm run setup
echo "Listo. Inicia con: cd $DEST && npm run dev  (http://localhost:3000)"
