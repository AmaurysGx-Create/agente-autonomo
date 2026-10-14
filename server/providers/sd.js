// Stable Diffusion local (imágenes). Gratis; funciona en CPU (lento) o GPU (rápido).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { ROOT } from '../paths.js';
import { pyEval, pyRun } from '../python.js';

const SCRIPT = path.join(ROOT, 'server', 'ai', 'image.py');
export const SD_MODEL = process.env.SD_MODEL || 'stabilityai/sdxl-turbo';

export const sdProvider = {
  id: 'sd',
  kind: 'image',
  name: `Stable Diffusion (${SD_MODEL.split('/').pop()})`,
  description: 'Genera imágenes a partir de texto en tu equipo. Con GPU tarda segundos; en CPU puede tardar minutos.',
  available: async () => (await pyEval('import torch, diffusers; print("ok")')) === 'ok',
  async generate(job, { output, onProgress, signal }) {
    const paramsFile = path.join(os.tmpdir(), `openfield-${job.id}.json`);
    fs.writeFileSync(paramsFile, JSON.stringify({ ...job.params, model: SD_MODEL, output }));
    try {
      await pyRun([SCRIPT, paramsFile], { onProgress, signal });
    } finally {
      fs.rmSync(paramsFile, { force: true });
    }
  },
};
