import React from 'react';

const TABS = [
  ['explore', 'Explorar'],
  ['create', 'Crear video'],
  ['cinema', 'Cinema Studio'],
  ['effects', 'Efectos'],
  ['gallery', 'Mis videos'],
];

export default function Nav({ tab, setTab, active, count }) {
  return (
    <header className="nav">
      <div className="logo">◐</div>
      <nav>
        {TABS.map(([id, label]) => (
          <button key={id} className={tab === id ? 'on' : ''} onClick={() => setTab(id)}>
            {label}
            {id === 'gallery' && count > 0 && <span className="badge">{count}</span>}
          </button>
        ))}
      </nav>
      <div className="spacer" />
      {active && <span className="pill pulse">Generando…</span>}
      <span className="pill free">100% gratis · local</span>
    </header>
  );
}
