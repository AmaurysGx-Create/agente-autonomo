import React, { useEffect, useState } from 'react';
import { applyEffect, getEffects } from '../api.js';
import VideoCard from '../components/VideoCard.jsx';

export default function Effects({ jobs, refresh }) {
  const [effects, setEffects] = useState({});
  const [effect, setEffect] = useState('vintage');
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { getEffects().then(setEffects).catch(() => {}); }, []);

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (!file) return setError('Sube un video primero');
    const fd = new FormData();
    fd.set('effect', effect);
    fd.set('video', file);
    setBusy(true);
    try { await applyEffect(fd); await refresh(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const mine = jobs.filter((j) => j.params.kind === 'effect').slice(0, 6);
  return (
    <main className="page create">
      <form className="panel" onSubmit={submit}>
        <h2>Efectos de video</h2>
        <label>
          Tu video (MP4, WEBM, MOV · máx. 25 MB)
          <input type="file" accept="video/mp4,video/webm,video/quicktime" onChange={(e) => setFile(e.target.files[0] || null)} />
        </label>
        <label>
          Efecto
          <div className="chips">
            {Object.entries(effects).map(([id, l]) => (
              <button type="button" key={id} className={effect === id ? 'on' : ''} onClick={() => setEffect(id)}>{l}</button>
            ))}
          </div>
        </label>
        {error && <p className="error">{error}</p>}
        <button className="cta" disabled={busy}>{busy ? 'Enviando…' : 'Aplicar efecto'}</button>
      </form>
      <section className="results">
        <h2 className="sec">Resultados</h2>
        {mine.length === 0 && <p className="empty">Aquí verás tus videos con efectos.</p>}
        <div className="grid">{mine.map((j) => <VideoCard key={j.id} job={j} />)}</div>
      </section>
    </main>
  );
}
