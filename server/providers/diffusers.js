// Proveedor opcional de IA generativa local (LTX-Video vía diffusers). Gratis, requiere GPU.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { ROOT } from '../paths.js';

const SCRIPT = path.join(ROOT, 'server', 'ai', 'generate.py');
const PYTHON =
  process.env.PYTHON ||
  [path.join(ROOT, '.venv', 'bin', 'python'), path.join(ROOT, '.venv', 'Scripts', 'python.exe')].find((p) => fs.existsSync(p)) ||
  'python3';

function check() {
  return new Promise((resolve) => {
    const p = spawn(PYTHON, ['-c', 'import torch, diffusers; print(torch.cuda.is_available())']);
    let out = '';
    p.stdout.on('data', (d) => (out += d));
    p.on('error', () => resolve(false));
    p.on('close', (c) => resolve(c === 0 && out.trim() === 'True'));
  });
}

export const diffusersProvider = {
  id: 'diffusers',
  name: 'IA local LTX-Video (gratis, GPU)',
  description: 'Modelo de video generativo open source que corre en tu PC. Texto→video e imagen→video reales.',
  modes: ['text', 'image'],
  available: check,
  async generate(job, { output, onProgress, signal }) {
    const paramsFile = path.join(os.tmpdir(), `openfield-${job.id}.json`);
    fs.writeFileSync(paramsFile, JSON.stringify({ ...job.params, output }));
    await new Promise((resolve, reject) => {
      const p = spawn(PYTHON, [SCRIPT, paramsFile]);
      let err = '';
      signal?.addEventListener('abort', () => p.kill('SIGKILL'));
      p.stdout.on('data', (d) => {
        const m = [...d.toString().matchAll(/PROGRESS ([\d.]+)/g)].pop();
        if (m) onProgress(Math.min(0.99, Number(m[1])));
      });
      p.stderr.on('data', (d) => (err += d));
      p.on('error', (e) => reject(new Error('No se pudo ejecutar Python: ' + e.message)));
      p.on('close', (c) => {
        fs.rmSync(paramsFile, { force: true });
        c === 0 ? resolve() : reject(new Error(err.split('\n').slice(-8).join('\n')));
      });
    });
  },
};
