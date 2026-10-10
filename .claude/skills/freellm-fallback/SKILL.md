---
name: freellm-fallback
description: Configura y usa FreeLLMAPI (34 proveedores con cuentas gratuitas en un solo endpoint) como modelo de respaldo de Claude Code, para continuar la misma conversación cuando se acaban los límites de Claude. Úsala cuando el usuario pida respaldo, "free fallback", o diga que se quedó sin límite/cuota.
---

# FreeLLM fallback para Claude Code

Router: https://github.com/tashfeenahmed/freellmapi (local, puerto 3001). Reúne ~34 proveedores gratuitos
y hace failover automático entre ellos. Con `FREELLMAPI_CONTEXT_HANDOFF=on_model_switch` el modelo nuevo
recibe un resumen y no reinicia la tarea.

## Limitación importante
Claude Code NO cambia solo de modelo cuando se acaba tu límite. El respaldo es un segundo arranque:
cierras la sesión y ejecutas `scripts/claude-free`, que reabre la MISMA conversación (`--continue`)
pero con el router gratuito como backend. Los modelos gratis son menos capaces que Claude.

## Instalación (una vez, en la máquina del usuario)
1. `scripts/freellm-setup.sh` (clona en ~/freellmapi, crea .env con ENCRYPTION_KEY, compila).
2. `scripts/freellm-start.sh` y abrir http://localhost:3001.
3. En la página **Keys**, el usuario crea cuentas gratis y pega sus API keys (Google AI Studio, Groq,
   Cerebras, Mistral, OpenRouter, Cloudflare, Cohere, NVIDIA, HuggingFace, etc.). Claude no puede crear
   esas cuentas ni ver las keys. Ordenar **Fallback Chain** a gusto.
4. `export FREELLMAPI_API_KEY=<unified key de la página Keys>` (ponerlo en ~/.bashrc o ~/.zshrc).

## Cuando se acabe el límite de Claude
`scripts/claude-free` → retoma la última sesión del directorio con el router.
Para elegir sesión: `scripts/claude-free --resume`. Para volver a Claude, abrir `claude` normal.

## Verificación
`npx freellmapi doctor claude --url http://localhost:3001` comprueba que Claude Code llega al router.

## Reglas para Claude
- No pegar ni imprimir keys en archivos del repo; usar variables de entorno.
- No usar `curl | bash`; usar los scripts del repo.
- Si el usuario pide "continuar donde quedó", ejecutar/indicar `scripts/claude-free`.
