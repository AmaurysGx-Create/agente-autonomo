// Proveedor opcional de IA generativa local (LTX-Video vía diffusers). Gratis, requiere GPU.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { ROOT } from '../paths.js';
import { pyEval, pyRun } from '../python.js';

const SCRIPT = path.join(ROOT, 'server', 'ai', 'generate.py');

export const diffusersProvider = {
  id: 'diffusers',
  kind: 'video',
  name: 'IA local LTX-Video (gratis, GPU)',
  description: 'Modelo de video generativo open source que corre en tu PC. Texto→video e imagen→video reales.',
  modes: ['text', 'image'],
  available: async () => (await pyEval('import torch, diffusers; print(torch.cuda.is_available())')) === 'True',
  async generate(job, { output, onProgress, signal }) {
    const paramsFile = path.join(os.tmpdir(), `openfield-${job.id}.json`);
    fs.writeFileSync(paramsFile, JSON.stringify({ ...job.params, output }));
    try {
      await pyRun([SCRIPT, paramsFile], { onProgress, signal });
    } finally {
      fs.rmSync(paramsFile, { force: true });
    }
  },
};
