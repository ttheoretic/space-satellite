// Einheitliche Darstellung von Alarmstufen. Farbe ist nie das einzige
// Merkmal: Jede Stufe hat zusätzlich ein eigenes Symbol und einen Text
// (wichtig bei Farbsehschwäche und auf schlechten Beamern).

import type { Severity } from "../types";

export const SEVERITY_ICON: Record<Severity, string> = { warning: "▲", critical: "◆" };
export const SEVERITY_LABEL: Record<Severity, string> = { warning: "WARNING", critical: "CRITICAL" };
export const SEVERITY_SHORT: Record<Severity, string> = { warning: "WARN", critical: "CRIT" };

export function SeverityBadge({ severity, short = false }: { severity: Severity; short?: boolean }) {
  return (
    <span className={`sev sev--${severity}`}>
      <span aria-hidden>{SEVERITY_ICON[severity]}</span>
      {short ? SEVERITY_SHORT[severity] : SEVERITY_LABEL[severity]}
    </span>
  );
}
