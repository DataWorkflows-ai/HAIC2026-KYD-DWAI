/** "Pin to dashboard" from any tab. Pins wait in localStorage until the dashboard adds them as widgets
 *  (it listens for PINNED and also drains the queue when it mounts). */
export type Pin = { type: string; title?: string; config: Record<string, unknown> };

const KEY = 'kyd_pins';
export const PINNED = 'kyd-pinned';

export function pinToDashboard(p: Pin) {
  try {
    const q: Pin[] = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    localStorage.setItem(KEY, JSON.stringify([...q, p]));
  } catch { /* storage unavailable: nothing to pin into */ }
  window.dispatchEvent(new Event(PINNED));
}

export function takePins(): Pin[] {
  try {
    const q: Pin[] = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    localStorage.removeItem(KEY);
    return q;
  } catch { return []; }
}
