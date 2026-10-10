#!/usr/bin/env bash
# Arranca el router FreeLLMAPI en segundo plano (puerto 3001) si no está corriendo.
set -euo pipefail
DIR="${FREELLM_DIR:-$HOME/freellmapi}"
if curl -fsS -m 2 http://localhost:3001/v1/models >/dev/null 2>&1 || curl -s -m 2 -o /dev/null http://localhost:3001/; then
  echo "FreeLLMAPI ya está corriendo en :3001"; exit 0
fi
cd "$DIR"
nohup npm run dev > "$DIR/router.log" 2>&1 &
echo "FreeLLMAPI arrancando (log: $DIR/router.log) → http://localhost:3001"
