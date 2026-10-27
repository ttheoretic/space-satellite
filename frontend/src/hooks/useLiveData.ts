// Zentraler Daten-Hook: verbindet sich per WebSocket mit dem Backend und hält
// Status, letztes Telemetrie-Paket, Verlauf und Bordereignisse aktuell.
//
// Bricht die Verbindung ab (z. B. Backend neu gestartet), versucht der Hook es
// automatisch erneut – mit wachsender Wartezeit (1 s, 2 s, 4 s … max. 10 s).

import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ConnectionState, Frame, SpacecraftEvent, Status } from "../types";

/** Höchstzahl der Punkte pro Diagramm – mehr bringt optisch nichts, kostet aber Rechenzeit. */
const MAX_POINTS = 600;

type ServerMessage =
  | { type: "telemetry"; frame: Frame }
  | { type: "status"; status: Status }
  | { type: "event"; event: SpacecraftEvent }
  | { type: "reset" };

export function useLiveData(windowMinutes: number) {
  const [status, setStatus] = useState<Status | null>(null);
  const [latest, setLatest] = useState<Frame | null>(null);
  const [history, setHistory] = useState<Frame[]>([]);
  const [events, setEvents] = useState<SpacecraftEvent[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  // Wird hochgezählt, wenn der Verlauf neu geladen werden soll
  const [reloadKey, setReloadKey] = useState(0);

  // Die WebSocket-Callbacks brauchen immer das aktuelle Zeitfenster
  const windowRef = useRef(windowMinutes);
  windowRef.current = windowMinutes;

  // Verlauf und Ereignisse per REST laden (beim Start, bei Fensterwechsel, nach Reconnect)
  useEffect(() => {
    let cancelled = false;
    api.history(windowMinutes, MAX_POINTS).then((h) => !cancelled && setHistory(h)).catch(() => {});
    api.events().then((e) => !cancelled && setEvents(e)).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [windowMinutes, reloadKey]);

  // WebSocket-Verbindung
  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: number | undefined;
    let delay = 1000;
    let disposed = false;

    const handle = (msg: ServerMessage) => {
      switch (msg.type) {
        case "telemetry":
          setLatest(msg.frame);
          setHistory((prev) => appendThinned(prev, msg.frame, windowRef.current));
          break;
        case "status":
          setStatus(msg.status);
          break;
        case "event":
          setEvents((prev) => [msg.event, ...prev].slice(0, 200));
          break;
        case "reset":
          setLatest(null);
          setReloadKey((k) => k + 1);
          break;
      }
    };

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws`);
      ws.onopen = () => {
        setConnection("live");
        delay = 1000;
        setReloadKey((k) => k + 1); // Lücke während der Trennung auffüllen
      };
      ws.onmessage = (e) => handle(JSON.parse(e.data) as ServerMessage);
      ws.onclose = () => {
        if (disposed) return;
        setConnection("offline");
        retryTimer = window.setTimeout(connect, delay);
        delay = Math.min(delay * 2, 10_000);
      };
    };

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  return { status, latest, history, events, connection };
}

/**
 * Hängt ein Live-Paket an den Verlauf an – aber nur, wenn seit dem letzten
 * gespeicherten Punkt genug Zeit vergangen ist. So bleiben es höchstens
 * ~MAX_POINTS Punkte, egal ob 1× oder 60× Zeitraffer. Ältere Punkte außerhalb
 * des Zeitfensters fallen heraus.
 */
function appendThinned(prev: Frame[], frame: Frame, windowMinutes: number): Frame[] {
  const t = Date.parse(frame.t);
  const spacingMs = (windowMinutes * 60_000) / MAX_POINTS;
  const last = prev[prev.length - 1];
  if (last) {
    const lastT = Date.parse(last.t);
    if (t < lastT) return [frame]; // Zeit lief rückwärts (Demo-Reset) → neu beginnen
    if (t - lastT < spacingMs) return prev;
  }
  const cutoff = t - windowMinutes * 60_000;
  let start = 0;
  while (start < prev.length && Date.parse(prev[start].t) < cutoff) start++;
  return [...prev.slice(start), frame];
}

/**
 * Missionszeit, die zwischen zwei Paketen flüssig weiterläuft (5× pro Sekunde),
 * auch im Zeitraffer.
 */
export function useMissionTime(latest: Frame | null, speed: number): number | null {
  const anchor = useRef<{ mission: number; real: number } | null>(null);
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    if (latest) anchor.current = { mission: Date.parse(latest.t), real: performance.now() };
  }, [latest]);

  useEffect(() => {
    const id = window.setInterval(() => {
      const a = anchor.current;
      // Höchstens 1,5 s vorausrechnen – bleibt die Verbindung weg, bleibt die Uhr stehen
      if (a) setNow(a.mission + Math.min(performance.now() - a.real, 1500) * speed);
    }, 200);
    return () => window.clearInterval(id);
  }, [speed]);

  return now;
}
