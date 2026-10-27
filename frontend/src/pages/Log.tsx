// Betriebsprotokoll: wer hat wann was getan (Grenzwerte, Alarm-Bestätigungen,
// ab Schritt 4 auch Befehle). Einträge können nicht geändert werden.

import { useEffect, useState } from "react";
import { api } from "../api";
import { formatDateTime } from "../format";
import type { AuditEntry } from "../types";

const ACTION_LABEL: Record<string, string> = {
  "alarm.ack": "Acknowledged alarm",
  "limits.update": "Changed limits",
  "station.update": "Changed ground station",
  "command.create": "Created command",
  "command.schedule": "Scheduled command",
  "command.approve": "Approved command",
  "command.reject": "Rejected command",
  "command.send": "Sent command",
  "command.cancel": "Cancelled command",
};

export function Log({ refreshKey }: { refreshKey: string }) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);

  useEffect(() => {
    api.audit().then(setEntries).catch(() => {});
  }, [refreshKey]);

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Operations Log</h1>
          <p className="muted small">Every operator action with person, mission time and wall-clock time.</p>
        </div>
      </div>
      <section className="panel">
        {entries.length === 0 ? (
          <p className="muted small">No actions logged yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Mission time (UTC)</th>
                <th>Wall clock (UTC)</th>
                <th>Who</th>
                <th>What</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td className="mono">{formatDateTime(Date.parse(e.mission_time))}</td>
                  <td className="mono muted">{formatDateTime(Date.parse(e.real_time))}</td>
                  <td className="strong">{e.user}</td>
                  <td>{ACTION_LABEL[e.action] ?? e.action}</td>
                  <td className="small">{describe(e)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

/** Details lesbar machen, z. B. "battery_temp: crit_low -5 · warn_low 0" */
function describe(e: AuditEntry): string {
  const d = e.details;
  if (e.action === "alarm.ack" && Array.isArray(d.alarms)) return (d.alarms as string[]).join(", ");
  if (e.action === "limits.update") {
    const fmt = (k: string) => (d[k] === null || d[k] === undefined ? "—" : String(d[k]));
    return `${d.label ?? d.param}: crit low ${fmt("crit_low")} · warn low ${fmt("warn_low")} · warn high ${fmt(
      "warn_high",
    )} · crit high ${fmt("crit_high")}${d.enabled === false ? " · disabled" : ""}`;
  }
  if (e.action.startsWith("command.")) {
    const extra = [
      d.pass_id && `pass ${d.pass_id}`,
      d.comment && `“${d.comment}”`,
      d.reason && `reason: ${d.reason}`,
      d.result && `spacecraft: ${d.result}`,
    ].filter(Boolean);
    return [d.command, ...extra].join(" · ");
  }
  if (e.action === "station.update") {
    return `${d.name}: ${d.lat}° N, ${d.lon}° E, ${d.alt_m} m, min. elevation ${d.min_elevation}°`;
  }
  return JSON.stringify(d);
}
