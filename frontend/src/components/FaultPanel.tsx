// Demo-Steuerung des Simulators: Fehler gezielt auslösen, beheben,
// Zufallsfehler ein/aus und Demo zurücksetzen.
// Bewusst als "Demo controls" gekennzeichnet – im echten Betrieb gibt es das nicht.

import { useEffect, useState } from "react";
import { api } from "../api";
import type { FaultType, Frame } from "../types";

interface Props {
  frame: Frame | null;
  randomFaults: boolean;
}

export function FaultPanel({ frame, randomFaults }: Props) {
  const [faults, setFaults] = useState<FaultType[]>([]);
  const active = new Set(frame?.faults ?? []);

  useEffect(() => {
    api.faults().then(setFaults).catch(() => {});
  }, []);

  return (
    <div className="faults">
      <p className="muted small">
        Demo controls – they act on the simulator, not on a spacecraft. Use them to show how
        anomalies appear in the telemetry and alarms.
      </p>

      <ul className="faults__list">
        {faults.map((f) => (
          <li key={f.key} className={`fault ${active.has(f.key) ? "fault--active" : ""}`}>
            <div className="fault__head">
              <span className="strong">{f.label}</span>
              {active.has(f.key) ? (
                <span className="fault__state">ACTIVE</span>
              ) : (
                <button className="btn btn--small btn--ghost" onClick={() => api.triggerFault(f.key)}>
                  Trigger
                </button>
              )}
            </div>
            <div className="small muted">{f.description}</div>
            {active.has(f.key) && <div className="small fault__recovery">Recovery: {f.recovery}</div>}
          </li>
        ))}
      </ul>

      <div className="faults__actions">
        <button className="btn btn--small btn--ghost" onClick={() => api.clearFaults()} disabled={!active.size}>
          Clear all faults
        </button>
        <label className="toggle">
          <input type="checkbox" checked={randomFaults} onChange={(e) => api.setRandomFaults(e.target.checked)} />
          Random faults
        </label>
        <button
          className="btn btn--small btn--ghost"
          onClick={() => {
            if (window.confirm("Reset the demo? Telemetry and alarms are cleared and mission time returns to now.")) {
              api.resetDemo();
            }
          }}
        >
          Reset demo
        </button>
      </div>
    </div>
  );
}
