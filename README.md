# Openfield — estudio local de video con IA, gratis

App web (React + Node) con una interfaz inspirada en la referencia de Higgsfield (Explorar, Crear video, Mis videos), pero que **genera video en tu propio equipo, sin créditos ni suscripción**, y es accesible desde cualquier dispositivo de tu red local.

## Arranque rápido

Requisitos: Node 18+ y FFmpeg en el PATH.

```bash
npm run install:all
npm run build
npm start
```

La consola muestra la URL local y la de red (`http://192.168.x.x:3000`): ábrela desde el móvil, tablet u otro PC de la misma red. (Si no abre, permite el puerto 3000 en el firewall.)

Desarrollo con recarga: `npm run dev` (cliente en :5173, API en :3000). Otro puerto: `PORT=8080 npm start`.

## Funciones

- **Imagen**: texto→imagen con Stable Diffusion local (hasta 4 variaciones, semilla y formato).
- **Audio**: texto a voz con Piper (11 voces en es/en/pt/fr/de/it), velocidad ajustable.
- **Video** (Crear): texto→video e imagen→video (motor FFmpeg o IA local).
- **Cinema Studio**: hasta 12 escenas (texto y/o imagen) unidas con transiciones en un solo video.
- **Efectos**: sube un video y aplica cámara lenta, acelerado, reversa, B/N, sepia, vintage, viñeta, espejo, glitch o ensueño.
- **Mis videos**: galería con descarga y borrado.

## Motores de generación

| Motor | Requisitos | Qué hace |
|---|---|---|
| **FFmpeg Motion** | Solo FFmpeg | Imagen→video con cámara virtual (zoom/paneo) y texto→video como escena animada con tu prompt. Rápido, sin GPU. |
| **Stable Diffusion** (imágenes) | Python + `diffusers` (GPU opcional) | Por defecto `stabilityai/sdxl-turbo` (rápido, ~4 pasos, usable en CPU). Cambia el modelo con `SD_MODEL=stable-diffusion-v1-5/stable-diffusion-v1-5`. Revisa la licencia del modelo si lo usarás comercialmente. |
| **Piper TTS** (audio) | `pip install piper-tts` | Voces neuronales offline. Cada voz se descarga una vez (~60 MB) a `data/voices/`. |
| **IA local LTX-Video** | GPU NVIDIA (~8 GB VRAM), Python | Video generativo real (texto→video e imagen→video) con el modelo open source `Lightricks/LTX-Video`. |

Activar los motores de IA (opcional; sin ellos Imagen y Audio aparecen deshabilitados y FFmpeg sigue funcionando):

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r server/ai/requirements.txt
```

Los modelos se descargan en el primer uso (SDXL-Turbo ~7 GB, LTX-Video ~10 GB) y necesitan internet esa vez. Si el servidor detecta torch+CUDA, el motor aparece habilitado en "Crear video". Variable `PYTHON` para usar otro intérprete; `FONT_FILE` para otra fuente del texto.

## Arquitectura

- `server/index.js` — API Express (`/api/generate`, `/api/jobs`, `/api/providers`), cola de un trabajo a la vez, sirve el frontend y los videos. Escucha en `0.0.0.0`.
- `server/providers/` — proveedores enchufables (`ffmpeg.js`, `diffusers.js`). Para añadir otro (ComfyUI, Wan, CogVideoX…) implementa `{id, name, description, available(), generate(job, {output, onProgress, signal})}`.
- `server/ai/generate.py` — worker de diffusers.
- `client/` — React + Vite.
- `data/` — videos, subidas y `jobs.json` (ignorados por git).

> La interfaz replica únicamente el diseño general; no usa logos, marcas ni activos de Higgsfield, y no se conecta a sus servicios. Los resultados de FFmpeg Motion no son video generativo; para eso usa el motor de IA local.
