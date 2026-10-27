// Kachel mit einem aktuellen Messwert: Name, großer Wert, Einheit.
// Bei verletzten Grenzwerten färbt sie sich gelb (Warnung) oder rot (kritisch)
// und zeigt zusätzlich Symbol und Kurztext.

import { formatNumber } from "../format";
import type { LimitRow, Parameter, Severity } from "../types";
import { SeverityBadge } from "./Severity";

interface Props {
  param: Parameter;
  value: number | undefined;
  status?: Severity;
  limits?: LimitRow;
  /** Zusatzzeile unter dem Wert, z. B. "charging" */
  sub?: string;
}

export function ValueTile({ param, value, status, limits, sub }: Props) {
  return (
    <div className={`tile ${status ? `tile--${status}` : ""}`} title={tooltip(param, limits)}>
      <div className="tile__label">{param.label}</div>
      <div className="tile__value">
        <span className="mono">{formatNumber(value, param.decimals)}</span>
        <span className="tile__unit">{param.unit}</span>
      </div>
      {(status || sub) && (
        <div className="tile__sub">
          {status && <SeverityBadge severity={status} />} {sub}
        </div>
      )}
    </div>
  );
}

/** Erklärung + aktuelle Grenzwerte als Tooltip */
function tooltip(param: Parameter, limits?: LimitRow): string {
  if (!limits || !limits.enabled) return param.description;
  const parts = [
    limits.crit_low !== null && `crit < ${limits.crit_low}`,
    limits.warn_low !== null && `warn < ${limits.warn_low}`,
    limits.warn_high !== null && `warn > ${limits.warn_high}`,
    limits.crit_high !== null && `crit > ${limits.crit_high}`,
  ].filter(Boolean);
  return parts.length ? `${param.description}\nLimits (${param.unit}): ${parts.join(" · ")}` : param.description;
}
