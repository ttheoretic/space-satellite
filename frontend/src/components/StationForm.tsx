// Formular für die Bodenstation. Nur Operator und Flight Director dürfen
// speichern; die Prüfung der Werte macht zusätzlich das Backend.

import { useEffect, useState } from "react";
import { api } from "../api";
import type { Station } from "../types";

// Ein paar Beispiel-Standorte (Koordinaten gerundet)
const PRESETS: Station[] = [
  { name: "TU Berlin", lat: 52.51, lon: 13.33, alt_m: 60, min_elevation: 5 },
  { name: "Uni Würzburg", lat: 49.78, lon: 9.97, alt_m: 270, min_elevation: 5 },
  { name: "Uni Stuttgart", lat: 48.75, lon: 9.1, alt_m: 480, min_elevation: 5 },
];

const FIELDS: { key: keyof Station; label: string; unit: string }[] = [
  { key: "lat", label: "Latitude", unit: "° N" },
  { key: "lon", label: "Longitude", unit: "° E" },
  { key: "alt_m", label: "Altitude", unit: "m" },
  { key: "min_elevation", label: "Min. elevation", unit: "°" },
];

export function StationForm({ station, canEdit }: { station: Station; canEdit: boolean }) {
  const [draft, setDraft] = useState<Record<keyof Station, string>>(() => toDraft(station));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => setDraft(toDraft(station)), [station]);
  const dirty = JSON.stringify(draft) !== JSON.stringify(toDraft(station));

  const save = async () => {
    setError(null);
    const next = { name: draft.name.trim() } as Station;
    for (const f of FIELDS) {
      const n = Number(draft[f.key].trim().replace(",", "."));
      if (draft[f.key].trim() === "" || Number.isNaN(n)) return setError(`${f.label}: please enter a number`);
      (next[f.key] as number) = n;
    }
    setBusy(true);
    try {
      await api.saveStation(next);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="station">
      <div className="station__grid">
        <label className="field field--wide">
          <span>Name</span>
          <input value={draft.name} disabled={!canEdit} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
        </label>
        {FIELDS.map((f) => (
          <label key={f.key} className="field">
            <span>
              {f.label} <span className="muted">({f.unit})</span>
            </span>
            <input
              className="mono"
              inputMode="decimal"
              value={draft[f.key]}
              disabled={!canEdit}
              onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
            />
          </label>
        ))}
      </div>
      {error && <p className="notice notice--error">{error}</p>}
      {canEdit ? (
        <div className="station__actions">
          <select
            aria-label="Load preset"
            value=""
            onChange={(e) => {
              const p = PRESETS.find((x) => x.name === e.target.value);
              if (p) setDraft(toDraft(p));
            }}
          >
            <option value="">Load preset…</option>
            {PRESETS.map((p) => (
              <option key={p.name}>{p.name}</option>
            ))}
          </select>
          <button className="btn btn--small" disabled={!dirty || busy} onClick={save}>
            Save station
          </button>
        </div>
      ) : (
        <p className="muted small">Read-only access – switch to an operator or flight director to edit.</p>
      )}
    </div>
  );
}

function toDraft(s: Station): Record<keyof Station, string> {
  return {
    name: s.name,
    lat: String(s.lat),
    lon: String(s.lon),
    alt_m: String(s.alt_m),
    min_elevation: String(s.min_elevation),
  };
}
