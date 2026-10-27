// Kachel mit einem aktuellen Messwert: Name, großer Wert, Einheit.
// Ab Schritt 2 färbt sie sich bei Grenzwertverletzungen gelb oder rot.

import { formatNumber } from "../format";
import type { Parameter } from "../types";

interface Props {
  param: Parameter;
  value: number | undefined;
  /** Zusatzzeile unter dem Wert, z. B. "charging" */
  sub?: string;
}

export function ValueTile({ param, value, sub }: Props) {
  return (
    <div className="tile" title={param.description}>
      <div className="tile__label">{param.label}</div>
      <div className="tile__value">
        <span className="mono">{formatNumber(value, param.decimals)}</span>
        <span className="tile__unit">{param.unit}</span>
      </div>
      {sub && <div className="tile__sub">{sub}</div>}
    </div>
  );
}
