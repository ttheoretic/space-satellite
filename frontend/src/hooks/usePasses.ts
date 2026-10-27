// Lädt die Überflüge und hält sie aktuell: neu laden, wenn sich Bodenstation
// oder TLE ändern, nach Reset/Vorspulen und sobald der erste Überflug vorbei ist.

import { useEffect, useState } from "react";
import { api } from "../api";
import type { Pass, PassesResponse, Status } from "../types";

export function usePasses(status: Status | null, missionTime: number | null, reloadKey: number) {
  const [data, setData] = useState<PassesResponse | null>(null);
  const station = status ? JSON.stringify(status.station) : "";
  const tleEpoch = status?.tle.epoch ?? "";

  // Ist der erste Überflug der Liste vorbei? Dann neu laden.
  const firstLos = data?.passes[0] ? Date.parse(data.passes[0].los) : null;
  const firstPassOver = firstLos !== null && missionTime !== null && missionTime > firstLos;

  useEffect(() => {
    if (!status) return;
    let cancelled = false;
    api.passes(48).then((d) => !cancelled && setData(d)).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [station, tleEpoch, reloadKey, firstPassOver, status !== null]);

  return data;
}

/** Läuft gerade ein Überflug, sonst der nächste. */
export function currentOrNextPass(passes: Pass[], now: number | null): { pass: Pass; inProgress: boolean } | null {
  if (now === null) return null;
  for (const p of passes) {
    if (Date.parse(p.los) < now) continue;
    return { pass: p, inProgress: Date.parse(p.aos) <= now };
  }
  return null;
}
