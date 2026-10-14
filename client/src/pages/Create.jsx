import React, { useEffect, useRef, useState } from 'react';
import { generate } from '../api.js';
import VideoCard from '../components/VideoCard.jsx';

const ASPECTS = ['16:9', '9:16', '1:1', '4:3'];
const MOTIONS = [
  ['zoom-in', 'Acercar'],
  ['zoom-out', 'Alejar'],
  ['pan-left', 'Paneo ←'],
  ['pan-right', 'Paneo →'],
  ['pan-up', 'Paneo ↑'],
];

export default function Create({ providers, preset, jobs, refresh }) {
  const [mode, setMode] = useState(preset?.mode || 'text');
  const [provider, setProvider] = useState(preset?.provider || 'ffmpeg');
  const [aspect, setAspect] = useState(preset?.aspect || '16:9');
  const [prompt, setPrompt] = useState(preset?.prompt || '');
  const [duration, setDuration] = useState(5);
  const [motion, setMotion] = useState('zoom-in');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const input = useRef();

  useEffect(() => {
    if (!file) return setPreview(null);
    const u = URL.createObjectURL(file);
    setPreview(u);
    return () => URL.revokeObjectURL(u);
  }, [file]);

  const vids = jobs.filter((j) => !j.params.kind && (!j.type || j.type === 'video'));
  const prov = providers.find((p) => p.id === provider);

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (mode === 'image' && !file) return setError('Sube una imagen primero');
    if (mode === 'text' && !prompt.trim()) return setError('Escribe un prompt');
    const fd = new FormData();
    fd.set('prompt', prompt);
    fd.set('provider', provider);
    fd.set('aspect', aspect);
    fd.set('duration', duration);
    fd.set('motion', motion);
    if (mode === 'image') fd.set('image', file);
    setBusy(true);
    try {
      await generate(fd);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const reuse = (j) => {
    setPrompt(j.params.prompt);
    setAspect(j.params.aspect);
    setDuration(j.params.duration);
    setProvider(j.provider);
  };

  return (
    <main className="page create">
      <form className="panel" onSubmit={submit}>
        <h2>Crear video</h2>

        <div className="seg">
          <button type="button" className={mode === 'text' ? 'on' : ''} onClick={() => setMode('text')}>Texto → Video</button>
          <button type="button" className={mode === 'image' ? 'on' : ''} onClick={() => setMode('image')}>Imagen → Video</button>
        </div>

        {mode === 'image' && (
          <div className="drop" onClick={() => input.current.click()}>
            {preview ? <img src={preview} alt="" /> : <span>Haz clic para subir una imagen (PNG, JPG, WEBP)</span>}
            <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => setFile(e.target.files[0] || null)} />
          </div>
        )}

        <label>
          Prompt {mode === 'image' && <small>(opcional: texto superpuesto o guía para la IA)</small>}
          <textarea
            rows={4}
            maxLength={500}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Un astronauta caminando sobre Marte al atardecer, cámara cinematográfica…"
          />
        </label>

        <label>
          Motor
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            {providers.map((p) => (
              <option key={p.id} value={p.id} disabled={!p.available}>
                {p.name}{p.available ? '' : ' — no disponible'}
              </option>
            ))}
          </select>
          {prov && <small>{prov.description}</small>}
        </label>

        <div className="row">
          <label>
            Formato
            <div className="chips">
              {ASPECTS.map((a) => (
                <button type="button" key={a} className={aspect === a ? 'on' : ''} onClick={() => setAspect(a)}>{a}</button>
              ))}
            </div>
          </label>
          <label>
            Duración: {duration}s
            <input type="range" min={2} max={provider === 'diffusers' ? 8 : 20} value={duration} onChange={(e) => setDuration(+e.target.value)} />
          </label>
        </div>

        {mode === 'image' && provider === 'ffmpeg' && (
          <label>
            Movimiento de cámara
            <div className="chips">
              {MOTIONS.map(([id, l]) => (
                <button type="button" key={id} className={motion === id ? 'on' : ''} onClick={() => setMotion(id)}>{l}</button>
              ))}
            </div>
          </label>
        )}

        {error && <p className="error">{error}</p>}
        <button className="cta" disabled={busy}>{busy ? 'Enviando…' : 'Generar video'}</button>
      </form>

      <section className="results">
        <h2 className="sec">Resultados</h2>
        {vids.length === 0 && <p className="empty">Tus videos aparecerán aquí.</p>}
        <div className="grid">{vids.slice(0, 6).map((j) => <VideoCard key={j.id} job={j} onReuse={reuse} />)}</div>
      </section>
    </main>
  );
}
