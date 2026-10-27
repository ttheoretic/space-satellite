// Kleine Hilfsfunktionen für die REST-API des Backends.

import type {
  Alarm,
  AuditEntry,
  FaultType,
  Frame,
  LimitRow,
  LimitValues,
  Parameter,
  PassesResponse,
  PassTrack,
  SpacecraftEvent,
  Station,
  Status,
  User,
} from "./types";

// Ausgewählte Person. Wird bei jeder Anfrage im Kopffeld mitgeschickt; das
// Backend prüft damit die Rechte. (Im fertigen Produkt: echtes Login.)
let currentUserId: string | null = null;
export function setApiUser(id: string | null): void {
  currentUserId = id;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (currentUserId) headers["X-OrbitDesk-User"] = currentUserId;
  const res = await fetch(path, { ...init, headers: { ...headers, ...(init?.headers ?? {}) } });
  if (!res.ok) {
    // FastAPI liefert Fehlermeldungen im Feld "detail"
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `${res.status} ${res.statusText}`;
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  status: () => request<Status>("/api/status"),
  parameters: () => request<Parameter[]>("/api/parameters"),
  users: () => request<User[]>("/api/users"),
  faults: () => request<FaultType[]>("/api/faults"),
  events: () => request<SpacecraftEvent[]>("/api/events"),
  audit: () => request<AuditEntry[]>("/api/audit"),
  history: (minutes: number, maxPoints = 600) =>
    request<Frame[]>(`/api/telemetry/history?minutes=${minutes}&max_points=${maxPoints}`),

  // Alarme & Grenzwerte
  alarms: () => request<Alarm[]>("/api/alarms"),
  alarmHistory: () => request<Alarm[]>("/api/alarms/history"),
  acknowledge: (ids?: number[]) => post<Alarm[]>("/api/alarms/ack", { ids: ids ?? null }),
  limits: () => request<LimitRow[]>("/api/limits"),
  saveLimits: (key: string, values: LimitValues) =>
    request<LimitRow[]>(`/api/limits/${key}`, { method: "PUT", body: JSON.stringify(values) }),
  resetLimits: (key: string) => post<LimitRow[]>(`/api/limits/${key}/reset`),

  // Bodenstation & Überflüge
  saveStation: (station: Station) =>
    request<Station>("/api/station", { method: "PUT", body: JSON.stringify(station) }),
  passes: (hours = 48) => request<PassesResponse>(`/api/passes?hours=${hours}`),
  pass: (id: string) => request<PassTrack>(`/api/passes/${id}`),
  jumpToNextPass: () => post("/api/sim/jump-to-next-pass"),

  // Demo-Steuerung
  setSpeed: (speed: number) => post("/api/sim/speed", { speed }),
  resetDemo: () => post("/api/sim/reset"),
  refreshTle: () => post<{ ok: boolean }>("/api/tle/refresh"),
  triggerFault: (key: string) => post(`/api/sim/faults/${key}`),
  clearFaults: () => post("/api/sim/faults/clear"),
  setRandomFaults: (enabled: boolean) => post("/api/sim/random-faults", { enabled }),
};
