import express from 'express';
import cors from 'cors';
import multer from 'multer';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { CLIENT_DIST, UPLOAD_DIR, VIDEO_DIR } from './paths.js';
import { createJob, updateJob, getJob, listJobs, deleteJob } from './jobs.js';
import { ffmpegProvider, EFFECTS } from './providers/ffmpeg.js';
import { diffusersProvider } from './providers/diffusers.js';

const PORT = Number(process.env.PORT) || 3000;
const providers = Object.fromEntries([ffmpegProvider, diffusersProvider].map((p) => [p.id, p]));
const availability = {};
const refreshAvailability = async () => {
  for (const p of Object.values(providers)) availability[p.id] = await p.available().catch(() => false);
};
refreshAvailability();

fs.mkdirSync(UPLOAD_DIR, { recursive: true });
fs.mkdirSync(VIDEO_DIR, { recursive: true });

const upload = multer({
  storage: multer.diskStorage({
    destination: UPLOAD_DIR,
    filename: (_req, file, cb) => cb(null, randomUUID() + path.extname(file.originalname).toLowerCase().replace(/[^.a-z0-9]/g, '')),
  }),
  limits: { fileSize: 25 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => cb(null, /^image\/(png|jpe?g|webp)$/.test(file.mimetype) || /^video\/(mp4|webm|quicktime|x-matroska)$/.test(file.mimetype)),
});


const app = express();
app.use(cors());
app.use(express.json());
app.use('/media/videos', express.static(VIDEO_DIR));
app.use('/media/uploads', express.static(UPLOAD_DIR));

app.get('/api/providers', async (_req, res) => {
  await refreshAvailability();
  res.json(
    Object.values(providers).map(({ id, name, description, modes }) => ({ id, name, description, modes, available: availability[id] }))
  );
});

app.get('/api/jobs', (_req, res) => res.json(listJobs()));
app.get('/api/jobs/:id', (req, res) => (getJob(req.params.id) ? res.json(getJob(req.params.id)) : res.sendStatus(404)));

app.post('/api/generate', upload.single('image'), (req, res) => {
  const { prompt = '', provider = 'ffmpeg', aspect = '16:9', motion = 'zoom-in' } = req.body;
  const duration = Math.min(30, Math.max(2, Number(req.body.duration) || 5));
  const p = providers[provider];
  if (!p) return res.status(400).json({ error: 'Proveedor desconocido' });
  if (!availability[provider]) return res.status(400).json({ error: `${p.name} no está disponible en este equipo` });
  if (req.file && !/^image\//.test(req.file.mimetype)) return res.status(400).json({ error: 'Sube una imagen PNG, JPG o WEBP' });
  if (!req.file && !prompt.trim()) return res.status(400).json({ error: 'Escribe un prompt o sube una imagen' });

  const job = createJob({
    provider,
    params: {
      prompt: prompt.trim().slice(0, 500),
      duration,
      aspect,
      motion,
      imagePath: req.file?.path,
      seed: req.body.seed ? Number(req.body.seed) : undefined,
    },
    imageUrl: req.file ? `/media/uploads/${req.file.filename}` : null,
  });
  enqueue(job.id);
  res.status(202).json(job);
});

app.get('/api/effects', (_req, res) => res.json(EFFECTS));

app.post('/api/effect', upload.single('video'), (req, res) => {
  if (!req.file || !/^video\//.test(req.file.mimetype)) return res.status(400).json({ error: 'Sube un archivo de video (mp4, webm, mov)' });
  if (!EFFECTS[req.body.effect]) return res.status(400).json({ error: 'Efecto desconocido' });
  const job = createJob({
    provider: 'ffmpeg',
    params: { kind: 'effect', effect: req.body.effect, prompt: EFFECTS[req.body.effect], aspect: 'orig', duration: 0, videoPath: req.file.path },
    uploads: [req.file.path],
  });
  enqueue(job.id);
  res.status(202).json(job);
});

// Cinema Studio: scenes = JSON [{prompt,duration}], imágenes opcionales en campos scene_0, scene_1…
app.post('/api/storyboard', upload.any(), (req, res) => {
  let scenes;
  try {
    scenes = JSON.parse(req.body.scenes);
  } catch {
    return res.status(400).json({ error: 'Escenas inválidas' });
  }
  if (!Array.isArray(scenes) || scenes.length < 1 || scenes.length > 12) return res.status(400).json({ error: 'Entre 1 y 12 escenas' });
  const byField = Object.fromEntries((req.files || []).map((f) => [f.fieldname, f]));
  const clean = scenes.map((s, i) => ({
    prompt: String(s.prompt || '').trim().slice(0, 300),
    duration: Math.min(10, Math.max(2, Number(s.duration) || 4)),
    imagePath: /^image\//.test(byField[`scene_${i}`]?.mimetype || '') ? byField[`scene_${i}`].path : undefined,
  }));
  if (clean.some((s) => !s.prompt && !s.imagePath)) return res.status(400).json({ error: 'Cada escena necesita texto o imagen' });
  const job = createJob({
    provider: 'ffmpeg',
    params: { kind: 'storyboard', scenes: clean, aspect: req.body.aspect || '16:9', prompt: clean.map((s) => s.prompt).filter(Boolean).join(' → ').slice(0, 200), duration: Math.round(clean.reduce((a, s) => a + s.duration, 0)) },
    uploads: clean.map((s) => s.imagePath).filter(Boolean),
  });
  enqueue(job.id);
  res.status(202).json(job);
});

app.delete('/api/jobs/:id', (req, res) => {
  const job = getJob(req.params.id);
  if (!job) return res.sendStatus(404);
  controllers.get(job.id)?.abort();
  if (job.file) fs.rmSync(path.join(VIDEO_DIR, job.file), { force: true });
  for (const f of job.uploads || []) fs.rmSync(f, { force: true });
  if (job.imageUrl) fs.rmSync(path.join(UPLOAD_DIR, path.basename(job.imageUrl)), { force: true });
  deleteJob(job.id);
  res.sendStatus(204);
});

// --- Cola: un trabajo a la vez (los modelos de IA consumen toda la GPU) ---
const queue = [];
const controllers = new Map();
let busy = false;

function enqueue(id) {
  queue.push(id);
  pump();
}

async function pump() {
  if (busy) return;
  const id = queue.shift();
  if (!id) return;
  const job = getJob(id);
  if (!job) return pump();
  busy = true;
  const ctrl = new AbortController();
  controllers.set(id, ctrl);
  const file = `${id}.mp4`;
  updateJob(id, { status: 'running', progress: 0.01 });
  try {
    await providers[job.provider].generate(job, {
      output: path.join(VIDEO_DIR, file),
      signal: ctrl.signal,
      onProgress: (progress) => updateJob(id, { progress }),
    });
    updateJob(id, { status: 'done', progress: 1, file, url: `/media/videos/${file}`, finishedAt: Date.now() });
  } catch (e) {
    if (getJob(id)) updateJob(id, { status: 'failed', error: String(e.message || e) });
  } finally {
    controllers.delete(id);
    busy = false;
    pump();
  }
}

// --- Frontend compilado ---
if (fs.existsSync(CLIENT_DIST)) {
  app.use(express.static(CLIENT_DIST));
  app.get('*', (_req, res) => res.sendFile(path.join(CLIENT_DIST, 'index.html')));
} else {
  app.get('/', (_req, res) => res.send('Frontend no compilado. Ejecuta: npm run build'));
}

// 0.0.0.0 => accesible desde otros dispositivos de la red local
app.listen(PORT, '0.0.0.0', () => {
  console.log(`\n  Openfield listo\n  Local:  http://localhost:${PORT}`);
  for (const addrs of Object.values(os.networkInterfaces()))
    for (const a of addrs || []) if (a.family === 'IPv4' && !a.internal) console.log(`  Red:    http://${a.address}:${PORT}`);
  console.log();
});
