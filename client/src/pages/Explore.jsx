import React from 'react';
import VideoCard from '../components/VideoCard.jsx';

const HERO = [
  { title: 'TEXTO A VIDEO', sub: 'Describe una escena y obtén un clip animado. Sin límites, sin pagos.', cls: 'g1', preset: { mode: 'text' } },
  { title: 'IMAGEN A VIDEO', sub: 'Sube una foto y dale movimiento de cámara cinematográfico.', cls: 'g2', preset: { mode: 'image' } },
  { title: 'MODO IA LOCAL', sub: 'Con GPU, genera video real con LTX-Video open source.', cls: 'g3', preset: { mode: 'text', provider: 'diffusers' } },
  { title: 'VERTICAL 9:16', sub: 'Clips listos para Reels, TikTok y Shorts.', cls: 'g4', preset: { mode: 'text', aspect: '9:16' } },
];

const TOOLS = [
  ['▶', 'Texto → Video', 'Escenas animadas desde un prompt', { mode: 'text' }],
  ['🖼', 'Imagen → Video', 'Zoom, paneo y fundidos cinematográficos', { mode: 'image' }],
  ['🤖', 'IA generativa', 'LTX-Video corriendo en tu GPU', { mode: 'text', provider: 'diffusers' }],
  ['📱', 'Formato vertical', 'Reels, TikTok y Shorts en 9:16', { mode: 'text', aspect: '9:16' }],
  ['🎞', 'Mis videos', 'Descarga y gestiona tus clips', 'gallery'],
  ['🌐', 'Acceso en red', 'Usa la app desde el móvil o la tablet', 'create'],
];

export default function Explore({ go, jobs }) {
  const recent = jobs.filter((j) => j.status === 'done').slice(0, 4);
  return (
    <main className="page">
      <section className="hero-row">
        {HERO.map((h) => (
          <button key={h.title} className="hero" onClick={() => go('create', h.preset)}>
            <div className={`hero-img ${h.cls}`}><span>{h.title}</span></div>
            <h3>{h.title}</h3>
            <p>{h.sub}</p>
          </button>
        ))}
      </section>

      <section className="promo-grid">
        <div className="promo">
          <h2>CREA TU VIDEO <em>GRATIS</em></h2>
          <ul>
            <li>✓ Sin créditos ni suscripción</li>
            <li>✓ Todo se procesa en tu equipo</li>
            <li>✓ Accesible desde toda tu red local</li>
          </ul>
          <button className="cta" onClick={() => go('create')}>Empezar a crear</button>
        </div>
        <div className="tools">
          {TOOLS.map(([icon, title, desc, target]) => (
            <button
              key={title}
              className="tool"
              onClick={() => (typeof target === 'string' ? go(target) : go('create', target))}
            >
              <span className="ico">{icon}</span>
              <b>{title}</b>
              <small>{desc}</small>
            </button>
          ))}
        </div>
      </section>

      {recent.length > 0 && (
        <section>
          <h2 className="sec">Tus últimos videos</h2>
          <div className="grid">{recent.map((j) => <VideoCard key={j.id} job={j} />)}</div>
        </section>
      )}
    </main>
  );
}
