// What this browser remembers: who you are in each decision, and the decisions
// you opened, so the home screen can list them. Lost storage only means
// joining again under a new name.
import type { Me } from './api';

export type Recent = { id: string; title: string };

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // private mode or full storage: the app still works for this visit
  }
}

export function getMe(decision: string): Me | null {
  return read<Record<string, Me>>('should-we:me', {})[decision] ?? null;
}

export function setMe(decision: string, me: Me) {
  write('should-we:me', { ...read<Record<string, Me>>('should-we:me', {}), [decision]: me });
}

export function recents(): Recent[] {
  return read<Recent[]>('should-we:recent', []);
}

export function remember(r: Recent) {
  write('should-we:recent', [r, ...recents().filter((x) => x.id !== r.id)].slice(0, 20));
}

export function forget(id: string) {
  write('should-we:recent', recents().filter((x) => x.id !== id));
}
