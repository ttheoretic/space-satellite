// Zeitraffer-Umschalter (1× / 10× / 60×). Gilt für alle Browser gleichzeitig,
// weil die Missionsuhr im Backend läuft.

import { useState } from "react";
import { api } from "../api";

export function SpeedControl({ speed, options }: { speed: number; options: number[] }) {
  const [busy, setBusy] = useState(false);

  const choose = async (s: number) => {
    setBusy(true);
    try {
      await api.setSpeed(s);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="segmented" role="group" aria-label="Simulation speed" title="Time-lapse factor">
      {options.map((s) => (
        <button
          key={s}
          className={s === speed ? "is-active" : ""}
          aria-pressed={s === speed}
          disabled={busy}
          onClick={() => choose(s)}
        >
          {s}×
        </button>
      ))}
    </div>
  );
}
