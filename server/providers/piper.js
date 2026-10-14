// Piper TTS (voz a partir de texto). Gratis, offline, rápido incluso en CPU.
import fs from 'node:fs';
import path from 'node:path';
import { DATA_DIR } from '../paths.js';
import { pyEval, pyRun } from '../python.js';

const VOICE_DIR = path.join(DATA_DIR, 'voices');

export const VOICES = {
  'es_ES-davefx-medium': 'Español (España) · Dave',
  'es_ES-sharvard-medium': 'Español (España) · Sharvard',
  'es_MX-claude-high': 'Español (México) · Claude',
  'es_AR-daniela-high': 'Español (Argentina) · Daniela',
  'en_US-lessac-medium': 'English (US) · Lessac',
  'en_US-amy-medium': 'English (US) · Amy',
  'en_GB-alan-medium': 'English (UK) · Alan',
  'pt_BR-faber-medium': 'Português (Brasil) · Faber',
  'fr_FR-siwis-medium': 'Français · Siwis',
  'de_DE-thorsten-medium': 'Deutsch · Thorsten',
  'it_IT-paola-medium': 'Italiano · Paola',
};

const model = (v) => path.join(VOICE_DIR, `${v}.onnx`);
const downloads = new Map(); // evita descargar la misma voz dos veces a la vez

async function ensureVoice(voice, signal) {
  if (fs.existsSync(model(voice)) && fs.existsSync(model(voice) + '.json')) return;
  if (!downloads.has(voice)) {
    fs.mkdirSync(VOICE_DIR, { recursive: true });
    const d = pyRun(['-m', 'piper.download_voices', voice, '--download-dir', VOICE_DIR], { signal })
      .catch((e) => {
        throw new Error(`No se pudo descargar la voz ${voice} (¿hay internet la primera vez?):\n${e.message}`);
      })
      .finally(() => downloads.delete(voice));
    downloads.set(voice, d);
  }
  await downloads.get(voice);
}

export const piperProvider = {
  id: 'piper',
  kind: 'audio',
  name: 'Piper TTS',
  description: 'Voces neuronales offline. La primera vez que usas una voz se descarga (~60 MB).',
  available: async () => (await pyEval('import piper; print("ok")')) === 'ok',
  async generate(job, { output, onProgress, signal }) {
    const { text, voice, speed = 1 } = job.params;
    if (!VOICES[voice]) throw new Error('Voz desconocida');
    onProgress(0.05);
    await ensureVoice(voice, signal);
    onProgress(0.4);
    // length-scale > 1 = más lento; se invierte para que "velocidad" sea intuitiva
    await pyRun(['-m', 'piper', '-m', model(voice), '-f', output, '--length-scale', String(1 / speed)], { signal, stdin: text });
  },
};
