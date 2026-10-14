import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from './paths.js';

export const PYTHON =
  process.env.PYTHON ||
  [path.join(ROOT, '.venv', 'bin', 'python'), path.join(ROOT, '.venv', 'Scripts', 'python.exe')].find((p) => fs.existsSync(p)) ||
  'python3';

// Ejecuta un snippet de Python y resuelve con su stdout (o null si falla)
export function pyEval(code) {
  return new Promise((resolve) => {
    const p = spawn(PYTHON, ['-c', code]);
    let out = '';
    p.stdout.on('data', (d) => (out += d));
    p.on('error', () => resolve(null));
    p.on('close', (c) => resolve(c === 0 ? out.trim() : null));
  });
}

// Lanza un proceso Python reportando progreso con líneas "PROGRESS 0.5"
export function pyRun(args, { onProgress, signal, stdin } = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(PYTHON, args);
    let err = '';
    signal?.addEventListener('abort', () => p.kill('SIGKILL'));
    p.stdout.on('data', (d) => {
      const m = [...d.toString().matchAll(/PROGRESS ([\d.]+)/g)].pop();
      if (m) onProgress?.(Math.min(0.99, Number(m[1])));
    });
    p.stderr.on('data', (d) => (err += d));
    p.on('error', (e) => reject(new Error('No se pudo ejecutar Python: ' + e.message)));
    p.on('close', (c) => (c === 0 ? resolve() : reject(new Error(err.split('\n').filter(Boolean).slice(-8).join('\n') || `Python terminó con código ${c}`))));
    if (stdin != null) p.stdin.end(stdin);
  });
}
