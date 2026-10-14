import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const DATA_DIR = path.join(ROOT, 'data');
export const UPLOAD_DIR = path.join(DATA_DIR, 'uploads');
export const VIDEO_DIR = path.join(DATA_DIR, 'videos');
export const CLIENT_DIST = path.join(ROOT, 'client', 'dist');
