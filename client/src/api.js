const j = async (r) => {
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `Error ${r.status}`);
  return r.status === 204 ? null : r.json();
};

export const getProviders = () => fetch('/api/providers').then(j);
export const getJobs = () => fetch('/api/jobs').then(j);
export const deleteJob = (id) => fetch(`/api/jobs/${id}`, { method: 'DELETE' }).then(j);
export const generate = (form) => fetch('/api/generate', { method: 'POST', body: form }).then(j);
