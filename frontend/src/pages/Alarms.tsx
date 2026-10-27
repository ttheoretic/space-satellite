// Alarmliste: offene Alarme (aktiv und/oder unbestätigt) mit Bestätigung,
// darunter das Archiv erledigter Alarme.

import { useEffect, useState } from "react";
import { api } from "../api";
import { SeverityBadge } from "../components/Severity";
import { formatDateTime, formatNumber } from "../format";
import type { Alarm, Frame, User } from "../types";

interface Props {
  alarms: Alarm[];
  latest: Frame | null;
  user: User | undefined;
}

export function Alarms({ alarms, latest, user }: Props) {
  const [history, setHistory] = useState<Alarm[]>([]);
  const [error, setError] = useState<string | null>(null);
  const canAck = !!user?.permissions.includes("alarm.ack");
  const unacked = alarms.filter((a) => !a.acknowledged);

  // Archiv neu laden, sobald sich die offenen Alarme ändern
  useEffect(() => {
    api.alarmHistory().then(setHistory).catch(() => {});
  }, [alarms]);

  const ack = async (ids?: number[]) => {
    setError(null);
    try {
      await api.acknowledge(ids);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const noAckReason = user ? `${user.name} (${user.role_label}) cannot acknowledge alarms` : "Select a user";

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Alarms</h1>
          <p className="muted small">
            An alarm stays in this list until its value is back within limits <em>and</em> someone has
            acknowledged it.
          </p>
        </div>
        <button
          className="btn"
          disabled={!canAck || !unacked.length}
          title={canAck ? undefined : noAckReason}
          onClick={() => ack()}
        >
          Acknowledge all ({unacked.length})
        </button>
      </div>
      {error && <p className="notice notice--error">{error}</p>}
      {!canAck && user && <p className="notice notice--info">{noAckReason} (read-only access).</p>}

      <section className="panel">
        <h2 className="panel__title">Open alarms</h2>
        {alarms.length === 0 ? (
          <p className="empty">✓ No open alarms. All parameters are within limits.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Parameter</th>
                <th>State</th>
                <th className="num">At raise</th>
                <th className="num">Now</th>
                <th>Limit</th>
                <th>Raised (UTC)</th>
                <th>Acknowledged</th>
              </tr>
            </thead>
            <tbody>
              {alarms.map((a) => (
                <tr key={a.id} className={!a.acknowledged ? `row--unacked row--${a.severity}` : ""}>
                  <td>
                    <SeverityBadge severity={a.severity} />
                  </td>
                  <td className="strong">{a.param_label}</td>
                  <td>
                    {a.active ? (
                      <span className="state state--active">ACTIVE</span>
                    ) : (
                      <span className="state state--cleared" title={`Cleared ${fmt(a.cleared_at)}`}>
                        BACK TO NORMAL
                      </span>
                    )}
                  </td>
                  <td className="num mono">
                    {formatNumber(a.value_at_raise, a.decimals)} {a.unit}
                  </td>
                  <td className="num mono">
                    {formatNumber(latest?.values[a.param_key], a.decimals)} {a.unit}
                  </td>
                  <td className="mono">{a.limit_text}</td>
                  <td className="mono">{fmt(a.raised_at)}</td>
                  <td>
                    {a.acknowledged ? (
                      <span className="muted small">
                        {a.acknowledged_by} · {fmt(a.acknowledged_at)}
                      </span>
                    ) : (
                      <button
                        className="btn btn--small"
                        disabled={!canAck}
                        title={canAck ? undefined : noAckReason}
                        onClick={() => ack([a.id])}
                      >
                        Acknowledge
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel">
        <h2 className="panel__title">History</h2>
        {history.length === 0 ? (
          <p className="muted small">No closed alarms yet.</p>
        ) : (
          <table className="table table--compact">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Parameter</th>
                <th>Limit</th>
                <th>Raised (UTC)</th>
                <th>Cleared (UTC)</th>
                <th>Acknowledged by</th>
              </tr>
            </thead>
            <tbody>
              {history.map((a) => (
                <tr key={a.id}>
                  <td>
                    <SeverityBadge severity={a.severity} short />
                  </td>
                  <td>{a.param_label}</td>
                  <td className="mono">{a.limit_text}</td>
                  <td className="mono">{fmt(a.raised_at)}</td>
                  <td className="mono">{fmt(a.cleared_at)}</td>
                  <td>{a.acknowledged_by}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

const fmt = (iso: string | null) => (iso ? formatDateTime(Date.parse(iso)) : "—");
