import React from 'react';
import VideoCard from '../components/VideoCard.jsx';

export default function Gallery({ jobs, onDelete, go }) {
  return (
    <main className="page">
      <h2 className="sec">Mis videos</h2>
      {jobs.length === 0 ? (
        <p className="empty">
          Aún no hay videos. <button className="link" onClick={() => go('create')}>Crea el primero</button>
        </p>
      ) : (
        <div className="grid">
          {jobs.map((j) => (
            <VideoCard
              key={j.id}
              job={j}
              onDelete={onDelete}
              onReuse={(job) => job.type === 'image' ? go('image', { prompt: job.params.prompt }) : job.type === 'audio' ? go('audio', { text: job.params.text, voice: job.params.voice }) : go('create', { mode: job.imageUrl ? 'image' : 'text', provider: job.provider, aspect: job.params.aspect, prompt: job.params.prompt })}
            />
          ))}
        </div>
      )}
    </main>
  );
}
