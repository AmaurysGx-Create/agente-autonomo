import React from 'react';

export default function VideoCard({ job, onDelete, onReuse }) {
  const { status, progress, url, params, error } = job;
  return (
    <article className="vcard">
      <div className={`thumb ${params.aspect === '9:16' ? 'tall' : ''}`}>
        {status === 'done' ? (
          <video src={url} controls loop muted playsInline preload="metadata" />
        ) : status === 'failed' ? (
          <div className="state err" title={error}>Error<small>{error?.slice(0, 160)}</small></div>
        ) : (
          <div className="state">
            <div className="bar"><i style={{ width: `${Math.round(progress * 100)}%` }} /></div>
            {status === 'queued' ? 'En cola…' : `Generando ${Math.round(progress * 100)}%`}
          </div>
        )}
      </div>
      <p className="prompt">{params.prompt || '(imagen animada)'}</p>
      <div className="meta">
        <span>{params.duration}s · {params.aspect}</span>
        <span className="actions">
          {status === 'done' && <a href={url} download={`video-${job.id.slice(0, 8)}.mp4`}>Descargar</a>}
          {onReuse && <button onClick={() => onReuse(job)}>Repetir</button>}
          {onDelete && <button onClick={() => onDelete(job.id)}>Borrar</button>}
        </span>
      </div>
    </article>
  );
}
