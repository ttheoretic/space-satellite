// Kleine Hilfsfunktionen für die REST-API des Backends.

import type { Frame, Parameter, SpacecraftEvent, Status } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    // FastAPI liefert Fehlermeldungen im Feld "detail"
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  status: () => request<Status>("/api/status"),
  parameters: () => request<Parameter[]>("/api/parameters"),
  events: () => request<SpacecraftEvent[]>("/api/events"),
  history: (minutes: number, maxPoints = 600) =>
    request<Frame[]>(`/api/telemetry/history?minutes=${minutes}&max_points=${maxPoints}`),
  setSpeed: (speed: number) => post("/api/sim/speed", { speed }),
  resetDemo: () => post("/api/sim/reset"),
  refreshTle: () => post<{ ok: boolean }>("/api/tle/refresh"),
};
