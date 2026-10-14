import React, { useEffect, useState } from 'react';
import { getVoices, makeSpeech } from '../api.js';
import VideoCard from '../components/VideoCard.jsx';

export default function AudioStudio({ jobs, refresh, available, preset }) {
  const [voices, setVoices] = useState({});
  const [voice, setVoice] = useState(preset?.voice || 'es_ES-davefx-medium');
  const [text, setText] = useState(preset?.text || '');
  const [speed, setSpeed] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { getVoices().then(setVoices).catch(() => {}); }, []);

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (!text.trim()) return setError('Escribe el texto a locutar');
    setBusy(true);
    try { await makeSpeech({ text, voice, speed }); await refresh(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const mine = jobs.filter((j) => j.type === 'audio').slice(0, 12);
  return (
    <main className="page create">
      <form className="panel" onSubmit={submit}>
        <h2>Audio · Texto a voz (Piper)</h2>
        {available === false && <p className="error">Piper no está instalado. Ejecuta <code>pip install piper-tts</code> (ver README).</p>}
        <label>Texto
          <textarea rows={7} maxLength={5000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Escribe lo que quieres que se diga…" />
        </label>
        <label>Voz <small>(la primera vez se descarga, necesita internet)</small>
          <select value={voice} onChange={(e) => setVoice(e.target.value)}>
            {Object.entries(voices).map(([id, l]) => <option key={id} value={id}>{l}</option>)}
          </select>
        </label>
        <label>Velocidad: {speed.toFixed(1)}×
          <input type="range" min={0.5} max={2} step={0.1} value={speed} onChange={(e) => setSpeed(+e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="cta" disabled={busy || available === false}>{busy ? 'Enviando…' : 'Generar audio'}</button>
      </form>
      <section className="results">
        <h2 className="sec">Resultados</h2>
        {mine.length === 0 && <p className="empty">Tus audios aparecerán aquí.</p>}
        <div className="grid">{mine.map((j) => <VideoCard key={j.id} job={j} />)}</div>
      </section>
    </main>
  );
}
