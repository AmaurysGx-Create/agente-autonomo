// Proveedor 100% gratuito y sin GPU: anima imágenes (Ken Burns) o genera
// escenas animadas a partir de texto usando solo FFmpeg.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const FONT_CANDIDATES = [
  process.env.FONT_FILE,
  'C:/Windows/Fonts/arialbd.ttf',
  '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
  '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
  '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
].filter(Boolean);
const FONT = FONT_CANDIDATES.find((f) => fs.existsSync(f));

const ASPECTS = {
  '16:9': [1280, 720],
  '9:16': [720, 1280],
  '1:1': [1024, 1024],
  '4:3': [1024, 768],
};

const PALETTES = [
  ['0x1a1a2e', '0xe94560'],
  ['0x0f2027', '0x2c5364'],
  ['0x42275a', '0x734b6d'],
  ['0x141e30', '0x243b55'],
  ['0x3a1c71', '0xffaf7b'],
  ['0x134e5e', '0x71b280'],
];

const esc = (s) =>
  s.replace(/\\/g, '\\\\').replace(/:/g, '\\:').replace(/'/g, '’').replace(/%/g, '\\%').replace(/,/g, '\\,');

function wrap(text, max) {
  const words = text.trim().split(/\s+/);
  const lines = [];
  let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > max) {
      lines.push(cur);
      cur = w;
    } else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  return lines.slice(0, 6);
}

function motionExpr(motion, frames) {
  // zoompan: z=zoom, x/y=esquina superior izquierda de la ventana
  const center = { x: 'iw/2-(iw/zoom/2)', y: 'ih/2-(ih/zoom/2)' };
  switch (motion) {
    case 'zoom-out':
      return { z: `max(1.0,1.4-on*0.4/${frames})`, ...center };
    case 'pan-left':
      return { z: '1.25', x: `(iw-iw/zoom)*(1-on/${frames})`, y: center.y };
    case 'pan-right':
      return { z: '1.25', x: `(iw-iw/zoom)*(on/${frames})`, y: center.y };
    case 'pan-up':
      return { z: '1.25', x: center.x, y: `(ih-ih/zoom)*(1-on/${frames})` };
    default:
      return { z: `min(1.0+on*0.4/${frames},1.4)`, ...center };
  }
}

function run(args, duration, onProgress, signal) {
  return new Promise((resolve, reject) => {
    const p = spawn('ffmpeg', ['-y', '-hide_banner', '-progress', 'pipe:1', '-nostats', ...args]);
    let err = '';
    signal?.addEventListener('abort', () => p.kill('SIGKILL'));
    p.stdout.on('data', (d) => {
      const m = /out_time_ms=(\d+)/.exec(d.toString());
      if (m) onProgress(Math.min(0.99, Number(m[1]) / 1e6 / duration));
    });
    p.stderr.on('data', (d) => (err += d));
    p.on('error', (e) => reject(new Error('FFmpeg no está instalado o no está en el PATH: ' + e.message)));
    p.on('close', (code) => (code === 0 ? resolve() : reject(new Error(err.split('\n').slice(-6).join('\n')))));
  });
}

const scene = {
  id: 'ffmpeg',
  name: 'FFmpeg Motion (gratis, sin GPU)',
  description: 'Anima imágenes con cámara virtual o crea escenas animadas desde texto. Rápido y funciona en cualquier PC.',
  modes: ['text', 'image'],
  async available() {
    return new Promise((resolve) => {
      const p = spawn('ffmpeg', ['-version']);
      p.on('error', () => resolve(false));
      p.on('close', (c) => resolve(c === 0));
    });
  },
  async generate(job, { output, onProgress, signal }) {
    const { prompt = '', duration = 5, aspect = '16:9', motion = 'zoom-in', imagePath } = job.params;
    const [w, h] = ASPECTS[aspect] || ASPECTS['16:9'];
    const fps = 25;
    const frames = duration * fps;
    const fontOpt = FONT ? `fontfile='${esc(FONT)}':` : '';
    const common = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '20', '-movflags', '+faststart', output];

    // Texto superpuesto con fundido de entrada
    const overlay = (text, size) =>
      wrap(text, aspect === '9:16' ? 18 : 34)
        .map(
          (line, i, arr) =>
            `drawtext=${fontOpt}text='${esc(line)}':fontcolor=white:fontsize=${size}:` +
            `borderw=3:bordercolor=black@0.6:x=(w-text_w)/2:y=(h-${arr.length * size * 1.3}-${Math.round(h * 0.08)})+${i}*${size * 1.3}:` +
            `alpha='min(1,max(0,(t-0.4)/0.8))'`
        )
        .join(',');

    if (imagePath) {
      const m = motionExpr(motion, frames);
      // se amplía la imagen antes de zoompan para evitar el temblor por redondeo
      const vf = [
        `scale=${w * 2}:${h * 2}:force_original_aspect_ratio=increase`,
        `crop=${w * 2}:${h * 2}`,
        `zoompan=z='${m.z}':x='${m.x}':y='${m.y}':d=${frames}:s=${w}x${h}:fps=${fps}`,
        'fade=t=in:st=0:d=0.5',
        `fade=t=out:st=${duration - 0.5}:d=0.5`,
        prompt && FONT ? overlay(prompt, Math.round(h / 20)) : null,
      ]
        .filter(Boolean)
        .join(',');
      await run(['-loop', '1', '-i', imagePath, '-t', String(duration), '-vf', vf, '-r', String(fps), ...common], duration, onProgress, signal);
    } else {
      if (!prompt.trim()) throw new Error('Escribe un prompt');
      const [c0, c1] = PALETTES[[...prompt].reduce((a, c) => a + c.charCodeAt(0), 0) % PALETTES.length];
      const src = `gradients=s=${w}x${h}:c0=${c0}:c1=${c1}:x0=0:y0=0:x1=${w}:y1=${h}:speed=0.015:duration=${duration}:rate=${fps}`;
      const vf = [
        'fade=t=in:st=0:d=0.5',
        `fade=t=out:st=${duration - 0.5}:d=0.5`,
        FONT ? overlay(prompt, Math.round(h / 14)) : null,
      ]
        .filter(Boolean)
        .join(',');
      await run(['-f', 'lavfi', '-i', src, '-vf', vf, ...common], duration, onProgress, signal);
    }
  },
};

// --- Efectos sobre un video subido (equivalente gratuito a "Efectos") ---
const W_EFFECTS = {
  slowmo: { vf: 'setpts=2.0*PTS', label: 'Cámara lenta' },
  fast: { vf: 'setpts=0.5*PTS', label: 'Acelerado' },
  reverse: { vf: 'reverse', label: 'Reversa' },
  bw: { vf: 'hue=s=0,eq=contrast=1.15', label: 'Blanco y negro' },
  sepia: { vf: 'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131', label: 'Sepia' },
  vintage: { vf: "curves=vintage,noise=alls=12:allf=t,vignette=PI/4", label: 'Vintage' },
  vignette: { vf: 'vignette=PI/3.5', label: 'Viñeta' },
  mirror: { vf: 'hflip', label: 'Espejo' },
  glitch: { vf: 'rgbashift=rh=-6:bh=6,noise=alls=20:allf=t', label: 'Glitch' },
  dream: { vf: 'gblur=sigma=2,eq=saturation=1.5:brightness=0.05', label: 'Ensueño' },
};
export const EFFECTS = Object.fromEntries(Object.entries(W_EFFECTS).map(([k, v]) => [k, v.label]));

function probeDuration(file) {
  return new Promise((resolve) => {
    const p = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file]);
    let out = '';
    p.stdout.on('data', (d) => (out += d));
    p.on('error', () => resolve(10));
    p.on('close', () => resolve(parseFloat(out) || 10));
  });
}

async function applyEffect(params, output, onProgress, signal) {
  const fx = W_EFFECTS[params.effect];
  if (!fx) throw new Error('Efecto desconocido');
  if (!params.videoPath) throw new Error('Sube un video');
  let dur = await probeDuration(params.videoPath);
  dur = Math.min(dur, 120);
  if (params.effect === 'slowmo') dur *= 2;
  if (params.effect === 'fast') dur /= 2;
  const common = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '20', '-movflags', '+faststart'];
  const timing = params.effect === 'slowmo' || params.effect === 'fast' || params.effect === 'reverse';
  // las alteraciones de tiempo no llevan audio; en el resto se conserva
  const audio = timing ? ['-an'] : ['-c:a', 'aac', '-map', '0:v:0', '-map', '0:a:0?'];
  await run(['-t', '120', '-i', params.videoPath, '-vf', `${fx.vf},scale=trunc(iw/2)*2:trunc(ih/2)*2`, ...audio, ...common, output], dur, onProgress, signal);
}

// --- Cinema Studio: varias escenas unidas con transiciones ---
async function renderStoryboard(params, output, onProgress, signal) {
  const scenes = params.scenes || [];
  if (scenes.length < 1) throw new Error('Añade al menos una escena');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'openfield-sb-'));
  const FADE = 0.6;
  try {
    const files = [];
    for (const [i, sc] of scenes.entries()) {
      const f = path.join(tmp, `s${i}.mp4`);
      await scene.generate(
        { params: { ...sc, aspect: params.aspect, motion: sc.motion || ['zoom-in', 'pan-right', 'zoom-out', 'pan-left'][i % 4] } },
        { output: f, onProgress: (p) => onProgress(((i + p) / (scenes.length + 1)) * 0.95), signal }
      );
      files.push(f);
    }
    if (files.length === 1) return fs.copyFileSync(files[0], output);
    let filter = '';
    let acc = scenes[0].duration;
    let last = '0:v';
    for (let i = 1; i < files.length; i++) {
      const out = i === files.length - 1 ? 'vout' : `v${i}`;
      filter += `[${last}][${i}:v]xfade=transition=fade:duration=${FADE}:offset=${(acc - FADE * i).toFixed(2)}[${out}];`;
      acc += scenes[i].duration;
      last = out;
    }
    const total = acc - FADE * (files.length - 1);
    await run(
      [...files.flatMap((f) => ['-i', f]), '-filter_complex', filter.slice(0, -1), '-map', '[vout]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '20', '-movflags', '+faststart', output],
      total,
      (p) => onProgress(0.95 + p * 0.05),
      signal
    );
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

export const ffmpegProvider = {
  ...scene,
  async generate(job, ctx) {
    const { kind = 'generate' } = job.params;
    if (kind === 'effect') return applyEffect(job.params, ctx.output, ctx.onProgress, ctx.signal);
    if (kind === 'storyboard') return renderStoryboard(job.params, ctx.output, ctx.onProgress, ctx.signal);
    return scene.generate(job, ctx);
  },
};
