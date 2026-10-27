// Formatierung von Zahlen und Zeiten. Alle Zeiten werden in UTC angezeigt –
// in der Raumfahrt üblich, damit Teams in verschiedenen Zeitzonen dieselbe
// Uhrzeit meinen.

export function formatNumber(value: number | undefined, decimals: number): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(decimals);
}

const pad = (n: number) => String(n).padStart(2, "0");

/** "2026-10-27 15:35:30" (UTC) */
export function formatDateTime(ms: number): string {
  const d = new Date(ms);
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`
  );
}

/** "15:35" bzw. mit Sekunden "15:35:30" (UTC) */
export function formatTime(ms: number, seconds = false): string {
  const d = new Date(ms);
  const hm = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
  return seconds ? `${hm}:${pad(d.getUTCSeconds())}` : hm;
}

/** Breite/Länge als "52.51° N" / "13.33° E" */
export function formatLat(lat: number): string {
  return `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? "N" : "S"}`;
}
export function formatLon(lon: number): string {
  return `${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? "E" : "W"}`;
}

/** Alter in Tagen lesbar: "6 h", "3.2 d" */
export function formatAgeDays(days: number): string {
  if (Math.abs(days) < 1) return `${Math.round(days * 24)} h`;
  return `${days.toFixed(1)} d`;
}

/** Zeitspanne lesbar: "1 h 23 min", "4 min 10 s", "35 s" */
export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h} h ${pad(m)} min`;
  if (m > 0) return `${m} min ${pad(s)} s`;
  return `${s} s`;
}

/** Azimut als Himmelsrichtung: 0° → "N", 135° → "SE" */
export function compass(az: number): string {
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round((((az % 360) + 360) % 360) / 45) % 8];
}
