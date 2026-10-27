// Grenzwert-Editor: pro Messwert Warn- und kritische Grenzen einstellen.
// Leeres Feld = keine Grenze in dieser Richtung.

import { useEffect, useState } from "react";
import { api } from "../api";
import { SeverityBadge } from "../components/Severity";
import { formatDateTime, formatNumber } from "../format";
import type { Frame, LimitRow, LimitValues, Parameter, User } from "../types";

const FIELDS = ["crit_low", "warn_low", "warn_high", "crit_high"] as const;
type Field = (typeof FIELDS)[number];

const GROUPS: { id: Parameter["group"]; label: string }[] = [
  { id: "power", label: "Power (EPS)" },
  { id: "thermal", label: "Thermal" },
  { id: "attitude", label: "Attitude (ADCS)" },
];

interface Props {
  params: Parameter[];
  limits: LimitRow[];
  latest: Frame | null;
  user: User | undefined;
}

export function Limits({ params, limits, latest, user }: Props) {
  const canEdit = !!user?.permissions.includes("limits.edit");
  const byKey = Object.fromEntries(limits.map((l) => [l.param_key, l]));

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Limits</h1>
          <p className="muted small">
            Yellow = warning, red = critical. An alarm is raised as soon as a value crosses a limit and
            clears once it is back inside with a small margin (hysteresis), so noisy values do not
            flap.
          </p>
        </div>
      </div>
      {!canEdit && user && (
        <p className="notice notice--info">
          {user.name} ({user.role_label}) has read-only access. Switch to an operator or flight director
          to edit limits.
        </p>
      )}

      {GROUPS.map((g) => (
        <section key={g.id} className="panel">
          <h2 className="panel__title">{g.label}</h2>
          <table className="table limits">
            <thead>
              <tr>
                <th>Parameter</th>
                <th className="num">Now</th>
                <th className="num th-crit">Critical low</th>
                <th className="num th-warn">Warning low</th>
                <th className="num th-warn">Warning high</th>
                <th className="num th-crit">Critical high</th>
                <th>Active</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {params
                .filter((p) => p.group === g.id)
                .map((p) => (
                  <LimitEditorRow
                    key={p.key}
                    param={p}
                    row={byKey[p.key]}
                    value={latest?.values[p.key]}
                    status={latest?.limits?.[p.key]}
                    canEdit={canEdit}
                  />
                ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

interface RowProps {
  param: Parameter;
  row: LimitRow | undefined;
  value: number | undefined;
  status: "warning" | "critical" | undefined;
  canEdit: boolean;
}

/** Eine Tabellenzeile mit eigenem Bearbeitungszustand ("Entwurf"). */
function LimitEditorRow({ param, row, value, status, canEdit }: RowProps) {
  const [draft, setDraft] = useState<Record<Field, string>>(() => toDraft(row));
  const [enabled, setEnabled] = useState(row?.enabled ?? true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Wenn jemand anderes die Grenzwerte ändert, Entwurf aktualisieren
  useEffect(() => {
    setDraft(toDraft(row));
    setEnabled(row?.enabled ?? true);
  }, [row]);

  const dirty =
    FIELDS.some((f) => draft[f] !== toDraft(row)[f]) || enabled !== (row?.enabled ?? true);

  const save = async () => {
    setError(null);
    const values: LimitValues = { crit_low: null, warn_low: null, warn_high: null, crit_high: null, enabled };
    for (const f of FIELDS) {
      const text = draft[f].trim().replace(",", ".");
      if (text === "") continue;
      const n = Number(text);
      if (Number.isNaN(n)) return setError(`"${draft[f]}" is not a number`);
      values[f] = n;
    }
    setBusy(true);
    try {
      await api.saveLimits(param.key, values);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    setError(null);
    try {
      await api.resetLimits(param.key);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <>
      <tr className={status ? `row--${status}` : ""}>
        <td>
          <div className="strong">{param.label}</div>
          <div className="muted small">
            {param.unit}
            {row?.updated_by && ` · changed by ${row.updated_by}, ${formatDateTime(Date.parse(row.updated_at!))}`}
          </div>
        </td>
        <td className="num">
          <span className="mono">{formatNumber(value, param.decimals)}</span>{" "}
          {status && <SeverityBadge severity={status} short />}
        </td>
        {FIELDS.map((f) => (
          <td key={f} className="num">
            <input
              className={`num-input ${f.startsWith("crit") ? "num-input--crit" : "num-input--warn"}`}
              inputMode="decimal"
              value={draft[f]}
              placeholder="—"
              disabled={!canEdit}
              aria-label={`${param.label} ${f.replace("_", " ")}`}
              onChange={(e) => setDraft({ ...draft, [f]: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && dirty && save()}
            />
          </td>
        ))}
        <td>
          <input
            type="checkbox"
            checked={enabled}
            disabled={!canEdit}
            onChange={(e) => setEnabled(e.target.checked)}
            aria-label={`${param.label} limits active`}
          />
        </td>
        <td className="limits__actions">
          {canEdit && (
            <>
              <button className="btn btn--small" disabled={!dirty || busy} onClick={save}>
                Save
              </button>
              <button className="btn btn--small btn--ghost" onClick={reset} title="Restore default limits">
                Default
              </button>
            </>
          )}
        </td>
      </tr>
      {error && (
        <tr>
          <td colSpan={8} className="limits__error">
            {error}
          </td>
        </tr>
      )}
    </>
  );
}

function toDraft(row: LimitRow | undefined): Record<Field, string> {
  const out = {} as Record<Field, string>;
  for (const f of FIELDS) out[f] = row?.[f] === null || row?.[f] === undefined ? "" : String(row[f]);
  return out;
}
