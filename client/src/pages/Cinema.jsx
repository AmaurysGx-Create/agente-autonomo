import React, { useState } from 'react';
import { makeStoryboard } from '../api.js';
import VideoCard from '../components/VideoCard.jsx';

const blank = () => ({ prompt: '', duration: 4, file: null });

export default function Cinema({ jobs, refresh }) {
  const [scenes, setScenes] = useState([blank(), blank()]);
  const [aspect, setAspect] = useState('16:9');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const set = (i, patch) => setScenes((s) => s.map((x, k) => (k === i ? { ...x, ...patch } : x)));

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (scenes.some((s) => !s.prompt.trim() && !s.file)) return setError('Cada escena necesita texto o imagen');
    const fd = new FormData();
    fd.set('aspect', aspect);
    fd.set('scenes', JSON.stringify(scenes.map(({ prompt, duration }) => ({ prompt, duration }))));
    scenes.forEach((s, i) => s.file && fd.set(`scene_${i}`, s.file));
    setBusy(true);
    try { await makeStoryboard(fd); await refresh(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const mine = jobs.filter((j) => j.params.kind === 'storyboard').slice(0, 6);
  const total = scenes.reduce((a, s) => a + s.duration, 0);
  return (
    <main className="page create">
      <form className="panel" onSubmit={submit}>
        <h2>Cinema Studio</h2>
        <small>Cada escena puede ser texto o una imagen animada. Se unen con transiciones suaves. Total ≈ {total}s</small>
        {scenes.map((s, i) => (
          <div className="scene" key={i}>
            <b>Escena {i + 1}</b>
            <textarea rows={2} maxLength={300} value={s.prompt} placeholder="Texto de la escena…" onChange={(e) => set(i, { prompt: e.target.value })} />
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => set(i, { file: e.target.files[0] || null })} />
            <label>Duración: {s.duration}s
              <input type="range" min={2} max={10} value={s.duration} onChange={(e) => set(i, { duration: +e.target.value })} />
            </label>
            {scenes.length > 1 && <button type="button" className="link" onClick={() => setScenes((x) => x.filter((_, k) => k !== i))}>Quitar escena</button>}
          </div>
        ))}
        {scenes.length < 12 && <button type="button" className="ghost" onClick={() => setScenes((s) => [...s, blank()])}>+ Añadir escena</button>}
        <label>Formato
          <div className="chips">
            {['16:9', '9:16', '1:1', '4:3'].map((a) => <button type="button" key={a} className={aspect === a ? 'on' : ''} onClick={() => setAspect(a)}>{a}</button>)}
          </div>
        </label>
        {error && <p className="error">{error}</p>}
        <button className="cta" disabled={busy}>{busy ? 'Enviando…' : 'Renderizar historia'}</button>
      </form>
      <section className="results">
        <h2 className="sec">Resultados</h2>
        {mine.length === 0 && <p className="empty">Tus historias aparecerán aquí.</p>}
        <div className="grid">{mine.map((j) => <VideoCard key={j.id} job={j} />)}</div>
      </section>
    </main>
  );
}
