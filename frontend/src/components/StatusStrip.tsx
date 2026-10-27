// Statusleiste oben im Dashboard: Betriebsmodus, Sonne/Eklipse, Heizung,
// Funkkontakt zur Bodenstation und Position über der Erde
// ("Subsatellitenpunkt" = Punkt direkt unter dem Satelliten).

import type { ReactNode } from "react";
import { formatDuration, formatLat, formatLon } from "../format";
import type { Frame, Pass } from "../types";

interface Props {
  frame: Frame | null;
  next: { pass: Pass; inProgress: boolean } | null;
  now: number | null;
}

const HEATER_MODE_LABEL = { AUTO: "auto", ON: "manual", OFF: "manual" } as const;

export function StatusStrip({ frame, next, now }: Props) {
  if (!frame) return <div className="strip strip--empty">Waiting for telemetry…</div>;
  const { mode, eclipse, illumination, heater_on, heater_mode, position } = frame;

  return (
    <div className="strip">
      <Item label="Mode">
        <span className={`pill ${mode === "NOMINAL" ? "pill--good" : "pill--warning"}`}>
          <span aria-hidden>{mode === "NOMINAL" ? "●" : "▲"}</span> {mode}
        </span>
      </Item>
      <Item label="Illumination">
        {eclipse ? (
          <span className="pill pill--neutral">
            <span aria-hidden>◐</span> ECLIPSE
          </span>
        ) : (
          <span className="pill pill--sun">
            <span aria-hidden>☀</span> SUNLIT {illumination < 1 ? `${Math.round(illumination * 100)} %` : ""}
          </span>
        )}
      </Item>
      <Item label="Battery heater">
        <span className="strong">{heater_on ? "ON" : "OFF"}</span>
        <span className="muted"> · {HEATER_MODE_LABEL[heater_mode]}</span>
      </Item>
      <Item label="Ground contact">
        {frame.contact?.in_contact ? (
          <span className="pill pill--good">
            <span aria-hidden>●</span> IN CONTACT · EL {frame.contact.elevation.toFixed(0)}°
          </span>
        ) : next && now !== null && !next.inProgress ? (
          <span>
            <span className="muted">Next AOS in </span>
            <span className="mono">{formatDuration(Date.parse(next.pass.aos) - now)}</span>
          </span>
        ) : (
          <span className="muted">No contact</span>
        )}
      </Item>
      <Item label="Sub-satellite point">
        <span className="mono">
          {formatLat(position.lat)} {formatLon(position.lon)}
        </span>
      </Item>
      <Item label="Altitude">
        <span className="mono">{position.alt_km.toFixed(1)} km</span>
      </Item>
    </div>
  );
}

function Item({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="strip__item">
      <div className="strip__label">{label}</div>
      <div className="strip__value">{children}</div>
    </div>
  );
}
