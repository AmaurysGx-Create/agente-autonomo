import React, { useState } from 'react';
import { makeImages } from '../api.js';
import VideoCard from '../components/VideoCard.jsx';

export default function ImageStudio({ jobs, refresh, available, preset }) {
  const [prompt, setPrompt] = useState(preset?.prompt || '');
  const [negative, setNegative] = useState('');
  const [aspect, setAspect] = useState('1:1');
  const [count, setCount] = useState(2);
  const [seed, setSeed] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (!prompt.trim()) return setError('Escribe un prompt');
    setBusy(true);
    try { await makeImages({ prompt, negative, aspect, count, seed }); await refresh(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const mine = jobs.filter((j) => j.type === 'image').slice(0, 12);
  return (
    <main className="page create">
      <form className="panel" onSubmit={submit}>
        <h2>Imagen con Stable Diffusion</h2>
        {available === false && <p className="error">Stable Diffusion no está instalado. Ejecuta <code>pip install -r server/ai/requirements.txt</code> (ver README).</p>}
        <label>Prompt
          <textarea rows={4} maxLength={500} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Retrato cinematográfico de un astronauta, luz dorada, 35mm…" />
        </label>
        <label>Prompt negativo <small>(solo modelos no-turbo)</small>
          <input value={negative} maxLength={300} onChange={(e) => setNegative(e.target.value)} placeholder="borroso, deforme, texto…" />
        </label>
        <label>Formato
          <div className="chips">
            {['1:1', '16:9', '9:16', '4:3'].map((a) => <button type="button" key={a} className={aspect === a ? 'on' : ''} onClick={() => setAspect(a)}>{a}</button>)}
          </div>
        </label>
        <div className="row">
          <label>Variaciones: {count}
            <input type="range" min={1} max={4} value={count} onChange={(e) => setCount(+e.target.value)} />
          </label>
          <label>Semilla <small>(vacío = aleatoria)</small>
            <input type="number" value={seed} onChange={(e) => setSeed(e.target.value)} />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <button className="cta" disabled={busy || available === false}>{busy ? 'Enviando…' : 'Generar imagen'}</button>
      </form>
      <section className="results">
        <h2 className="sec">Resultados</h2>
        {mine.length === 0 && <p className="empty">Tus imágenes aparecerán aquí.</p>}
        <div className="grid">{mine.map((j) => <VideoCard key={j.id} job={j} />)}</div>
      </section>
    </main>
  );
}
