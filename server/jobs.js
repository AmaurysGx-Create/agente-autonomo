import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { DATA_DIR } from './paths.js';

const FILE = path.join(DATA_DIR, 'jobs.json');
const jobs = new Map();

try {
  for (const j of JSON.parse(fs.readFileSync(FILE, 'utf8'))) {
    // un trabajo que quedó a medias al apagar el servidor se marca como fallido
    if (j.status === 'queued' || j.status === 'running') {
      j.status = 'failed';
      j.error = 'El servidor se reinició durante la generación';
    }
    jobs.set(j.id, j);
  }
} catch {}

function persist() {
  fs.writeFile(FILE, JSON.stringify([...jobs.values()]), () => {});
}

export function createJob(fields) {
  const job = {
    id: randomUUID(),
    status: 'queued',
    progress: 0,
    createdAt: Date.now(),
    ...fields,
  };
  jobs.set(job.id, job);
  persist();
  return job;
}

export function updateJob(id, patch) {
  const job = jobs.get(id);
  if (!job) return null;
  Object.assign(job, patch);
  persist();
  return job;
}

export const getJob = (id) => jobs.get(id);
export const listJobs = () => [...jobs.values()].sort((a, b) => b.createdAt - a.createdAt);

export function deleteJob(id) {
  const ok = jobs.delete(id);
  if (ok) persist();
  return ok;
}
