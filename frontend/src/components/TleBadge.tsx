// Zeigt, welche Bahndaten (TLE) verwendet werden und wie alt sie sind.
// Ein Klick öffnet Details und einen Knopf zum Neuladen.

import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { formatAgeDays, formatDateTime } from "../format";
import type { TleStatus } from "../types";

const SOURCE_LABEL: Record<TleStatus["source"], string> = {
  live: "LIVE",
  cache: "CACHED",
  fallback: "FALLBACK",
};

export function TleBadge({ tle }: { tle: TleStatus }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const tooOld = tle.age_days >= tle.warn_age_days;

  // Klick außerhalb schließt das Fenster
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const refresh = async () => {
    setBusy(true);
    try {
      await api.refreshTle();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="tle" ref={ref}>
      <button
        className={`tle__badge ${tle.warn ? "tle__badge--warn" : ""}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        title="Orbit data (TLE) used for orbit and pass prediction"
      >
        {tle.warn && <span aria-hidden>⚠ </span>}
        TLE {SOURCE_LABEL[tle.source]} · {formatAgeDays(tle.age_days)}
      </button>

      {open && (
        <div className="popover tle__popover" role="dialog" aria-label="TLE details">
          <h3>Orbit data (TLE)</h3>
          {tle.source === "fallback" && (
            <p className="notice notice--warn">
              Built-in fallback TLE. It only approximates the real orbit. CelesTrak could not be
              reached{tle.last_error ? ` (${tle.last_error})` : ""}.
            </p>
          )}
          {tooOld && (
            <p className="notice notice--warn">
              TLE is {formatAgeDays(tle.age_days)} old (limit {tle.warn_age_days} d). Orbit and pass
              predictions may be inaccurate.
            </p>
          )}
          <dl className="kv">
            <dt>Object</dt>
            <dd>{tle.name} (NORAD {tle.norad_id})</dd>
            <dt>Source</dt>
            <dd>{SOURCE_LABEL[tle.source]}</dd>
            <dt>Epoch</dt>
            <dd className="mono">{formatDateTime(Date.parse(tle.epoch))} UTC</dd>
            <dt>Age</dt>
            <dd>{formatAgeDays(tle.age_days)} (relative to mission time)</dd>
            <dt>Downloaded</dt>
            <dd className="mono">
              {tle.fetched_at ? `${formatDateTime(Date.parse(tle.fetched_at))} UTC` : "—"}
            </dd>
          </dl>
          <pre className="tle__lines">{`${tle.line1}\n${tle.line2}`}</pre>
          <button className="btn" onClick={refresh} disabled={busy}>
            {busy ? "Loading…" : "Reload from CelesTrak"}
          </button>
        </div>
      )}
    </div>
  );
}
