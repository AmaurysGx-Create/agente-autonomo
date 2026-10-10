#!/usr/bin/env bash
# Instala FreeLLMAPI (router de 34 proveedores gratis) en ~/freellmapi. Requiere Docker o Node >= 20.18.
set -euo pipefail
DIR="${FREELLM_DIR:-$HOME/freellmapi}"
if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 https://github.com/tashfeenahmed/freellmapi.git "$DIR"
fi
cd "$DIR"
if [ ! -f .env ]; then
  printf 'ENCRYPTION_KEY=%s\nPORT=3001\nFREELLMAPI_CONTEXT_HANDOFF=on_model_switch\n' \
    "$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")" > .env
fi
npm install
npm run build
echo "Listo. Inicia el router con: scripts/freellm-start.sh"
echo "Luego abre http://localhost:3001, añade tus keys gratis en 'Keys' y copia la unified key."
