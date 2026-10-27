// Dashboard: Live-Werte nach Subsystem, Verlaufsdiagramme, Bordereignisse
// und Simulator-Steuerung.

import { useMemo } from "react";
import { EventLog } from "../components/EventLog";
import { FaultPanel } from "../components/FaultPanel";
import { StatusStrip } from "../components/StatusStrip";
import { type ChartRow, TrendChart } from "../components/TrendChart";
import { ValueTile } from "../components/ValueTile";
import { CHART } from "../theme";
import type { Frame, LimitRow, Parameter, SpacecraftEvent } from "../types";

const WINDOWS = [
  { minutes: 30, label: "30 min" },
  { minutes: 180, label: "3 h" },
  { minutes: 720, label: "12 h" },
];

const [BLUE, ORANGE, AQUA] = CHART.series;

interface Props {
  params: Parameter[];
  latest: Frame | null;
  history: Frame[];
  events: SpacecraftEvent[];
  limits: LimitRow[];
  randomFaults: boolean;
  windowMinutes: number;
  onWindowChange: (minutes: number) => void;
}

export function Dashboard(props: Props) {
  const { params, latest, history, events, limits, randomFaults, windowMinutes, onWindowChange } = props;
  const P = useMemo(() => Object.fromEntries(params.map((p) => [p.key, p])), [params]);
  const L = useMemo(() => Object.fromEntries(limits.map((l) => [l.param_key, l])), [limits]);

  // Verlauf + jüngstes Paket in Diagrammzeilen umwandeln
  const rows = useMemo<ChartRow[]>(() => {
    const frames = [...history];
    if (latest && (!frames.length || Date.parse(latest.t) > Date.parse(frames[frames.length - 1].t))) {
      frames.push(latest);
    }
    return frames.map((f) => ({ x: Date.parse(f.t), eclipse: f.eclipse, ...f.values }));
  }, [history, latest]);

  if (!params.length) return <p className="muted">Loading…</p>;

  const v = latest?.values ?? {};
  const status = latest?.limits ?? {};
  // Kacheln einer Gruppe; fehlende Parameter werden übersprungen
  const tiles = (keys: string[], subs: Record<string, string | undefined> = {}) =>
    keys
      .filter((k) => P[k])
      .map((k) => (
        <ValueTile key={k} param={P[k]} value={v[k]} status={status[k]} limits={L[k]} sub={subs[k]} />
      ));

  const current = v.battery_current;
  const currentSub = current === undefined ? undefined : current > 0.05 ? "charging" : current < -0.05 ? "discharging" : "idle";

  return (
    <div className="dashboard">
      <StatusStrip frame={latest} />

      <div className="panels">
        <section className="panel">
          <h2 className="panel__title">Power <span className="muted">EPS</span></h2>
          <div className="tiles">
            {tiles(["battery_soc", "battery_voltage", "battery_current", "solar_power", "power_consumption"], {
              battery_current: currentSub,
            })}
          </div>
        </section>
        <section className="panel">
          <h2 className="panel__title">Thermal</h2>
          <div className="tiles">{tiles(["battery_temp", "obc_temp", "panel_temp"])}</div>
        </section>
        <section className="panel">
          <h2 className="panel__title">Attitude <span className="muted">ADCS</span></h2>
          <div className="tiles">{tiles(["pointing_error", "angular_rate", "roll", "pitch", "yaw"])}</div>
        </section>
      </div>

      <div className="toolbar">
        <h2 className="section-title">Trends</h2>
        <span className="muted small">Shaded areas = eclipse</span>
        <div className="segmented" role="group" aria-label="Trend window">
          {WINDOWS.map((w) => (
            <button
              key={w.minutes}
              className={w.minutes === windowMinutes ? "is-active" : ""}
              aria-pressed={w.minutes === windowMinutes}
              onClick={() => onWindowChange(w.minutes)}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      <div className="charts">
        <TrendChart title="State of Charge" unit="%" decimals={1} data={rows} limits={L.battery_soc}
          series={[{ key: "battery_soc", label: "SoC", color: BLUE }]} />
        <TrendChart title="Power Balance" unit="W" decimals={1} data={rows}
          series={[
            { key: "solar_power", label: "Solar", color: BLUE },
            { key: "power_consumption", label: "Power draw", color: ORANGE },
          ]} />
        <TrendChart title="Battery Temperature" unit="°C" decimals={1} data={rows} limits={L.battery_temp}
          series={[{ key: "battery_temp", label: "Battery", color: BLUE }]} />
        <TrendChart title="Structure Temperatures" unit="°C" decimals={1} data={rows}
          series={[
            { key: "obc_temp", label: "OBC", color: ORANGE },
            { key: "panel_temp", label: "Panel", color: AQUA },
          ]} />
        <TrendChart title="Pointing Error" unit="°" decimals={2} data={rows} limits={L.pointing_error}
          series={[{ key: "pointing_error", label: "Pointing error", color: BLUE }]} />
        <TrendChart title="Angular Rate" unit="°/s" decimals={3} data={rows} limits={L.angular_rate}
          series={[{ key: "angular_rate", label: "Angular rate", color: BLUE }]} />
      </div>

      <div className="panels panels--bottom">
        <section className="panel panel--wide">
          <h2 className="panel__title">Onboard Events</h2>
          <EventLog events={events} />
        </section>
        <section className="panel">
          <h2 className="panel__title">Simulation</h2>
          <FaultPanel frame={latest} randomFaults={randomFaults} />
        </section>
      </div>
    </div>
  );
}
