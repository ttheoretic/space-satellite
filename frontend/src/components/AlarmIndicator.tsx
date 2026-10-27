// Alarmanzeige in der Navigationsleiste: Wie viele Alarme sind aktiv bzw.
// unbestätigt? Ein Klick führt zur Alarmliste.

import type { Alarm } from "../types";
import { SEVERITY_ICON } from "./Severity";

export function AlarmIndicator({ alarms, onClick }: { alarms: Alarm[]; onClick: () => void }) {
  const active = alarms.filter((a) => a.active);
  const unacked = alarms.filter((a) => !a.acknowledged);
  const critical = active.some((a) => a.current === "critical");
  const warning = active.length > 0;

  if (!alarms.length) {
    return (
      <button className="alarm-ind alarm-ind--ok" onClick={onClick} title="All parameters within limits">
        <span aria-hidden>✓</span> NO ALARMS
      </button>
    );
  }

  const level = critical ? "critical" : warning ? "warning" : "neutral";
  return (
    <button
      className={`alarm-ind alarm-ind--${level} ${unacked.length ? "alarm-ind--unacked" : ""}`}
      onClick={onClick}
      title="Open alarm list"
    >
      <span aria-hidden>{critical ? SEVERITY_ICON.critical : SEVERITY_ICON.warning}</span>
      {active.length} ACTIVE
      {unacked.length > 0 && <span className="alarm-ind__unack">{unacked.length} UNACK</span>}
    </button>
  );
}
