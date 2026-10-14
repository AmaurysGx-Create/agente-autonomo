import React, { useCallback, useEffect, useState } from 'react';
import { getJobs, getProviders, deleteJob } from './api.js';
import Nav from './components/Nav.jsx';
import Explore from './pages/Explore.jsx';
import Create from './pages/Create.jsx';
import Cinema from './pages/Cinema.jsx';
import Effects from './pages/Effects.jsx';
import ImageStudio from './pages/ImageStudio.jsx';
import AudioStudio from './pages/AudioStudio.jsx';
import Gallery from './pages/Gallery.jsx';

export default function App() {
  const [tab, setTab] = useState('explore');
  const [jobs, setJobs] = useState([]);
  const [providers, setProviders] = useState([]);
  const [preset, setPreset] = useState(null);

  const refresh = useCallback(() => getJobs().then(setJobs).catch(() => {}), []);

  useEffect(() => {
    refresh();
    getProviders().then(setProviders).catch(() => {});
  }, [refresh]);

  // sondeo mientras haya trabajos activos
  const active = jobs.some((j) => j.status === 'queued' || j.status === 'running');
  useEffect(() => {
    if (!active) return;
    const t = setInterval(refresh, 1000);
    return () => clearInterval(t);
  }, [active, refresh]);

  const go = (t, p) => {
    setPreset(p || null);
    setTab(t);
    window.scrollTo(0, 0);
  };

  return (
    <>
      <Nav tab={tab} setTab={(t) => go(t)} active={active} count={jobs.length} />
      {tab === 'explore' && <Explore go={go} jobs={jobs} />}
      {tab === 'create' && <Create providers={providers.filter((p) => p.kind === 'video')} preset={preset} jobs={jobs} refresh={refresh} />}
      {tab === 'image' && <ImageStudio preset={preset} jobs={jobs} refresh={refresh} available={providers.find((p) => p.id === 'sd')?.available} />}
      {tab === 'audio' && <AudioStudio preset={preset} jobs={jobs} refresh={refresh} available={providers.find((p) => p.id === 'piper')?.available} />}
      {tab === 'cinema' && <Cinema jobs={jobs} refresh={refresh} />}
      {tab === 'effects' && <Effects jobs={jobs} refresh={refresh} />}
      {tab === 'gallery' && (
        <Gallery jobs={jobs} onDelete={(id) => deleteJob(id).then(refresh)} go={go} />
      )}
    </>
  );
}
