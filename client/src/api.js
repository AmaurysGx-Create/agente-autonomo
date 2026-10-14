const j = async (r) => {
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `Error ${r.status}`);
  return r.status === 204 ? null : r.json();
};

export const getProviders = () => fetch('/api/providers').then(j);
export const getJobs = () => fetch('/api/jobs').then(j);
export const deleteJob = (id) => fetch(`/api/jobs/${id}`, { method: 'DELETE' }).then(j);
export const generate = (form) => fetch('/api/generate', { method: 'POST', body: form }).then(j);
export const getEffects = () => fetch('/api/effects').then(j);
export const applyEffect = (form) => fetch('/api/effect', { method: 'POST', body: form }).then(j);
export const makeStoryboard = (form) => fetch('/api/storyboard', { method: 'POST', body: form }).then(j);
const post = (url, body) =>
  fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(j);
export const makeImages = (body) => post('/api/image', body);
export const getVoices = () => fetch('/api/voices').then(j);
export const makeSpeech = (body) => post('/api/tts', body);
