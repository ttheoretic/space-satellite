// Verlaufsdiagramm für eine oder mehrere Messgrößen mit derselben Einheit.
//
// Gestaltungsregeln:
//  - genau eine y-Achse (zwei Achsen täuschen Zusammenhänge vor)
//  - dünne Linien, dezentes Gitter
//  - Eklipse-Phasen als graue Hinterlegung, damit man Ursache und Wirkung sieht
//  - Fadenkreuz mit Tooltip beim Überfahren mit der Maus

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber, formatTime } from "../format";
import { CHART } from "../theme";

export interface ChartRow {
  x: number; // Zeit in ms (UTC)
  eclipse: boolean;
  [key: string]: number | boolean;
}

export interface SeriesDef {
  key: string;
  label: string;
  color: string;
}

interface Props {
  title: string;
  unit: string;
  decimals: number;
  data: ChartRow[];
  series: SeriesDef[];
  height?: number;
  /** Wertebereich der y-Achse; Standard: automatisch aus den Daten */
  yDomain?: [number | "auto", number | "auto" | ((dataMax: number) => number)];
}

export function TrendChart({ title, unit, decimals, data, series, height = 170, yDomain }: Props) {
  const eclipses = useMemo(() => eclipseIntervals(data), [data]);
  const latest = data[data.length - 1];

  return (
    <figure className="chart">
      <figcaption className="chart__head">
        <span className="chart__title">
          {title} <span className="muted">({unit})</span>
        </span>
        {/* Legende ab zwei Reihen – mit aktuellem Wert, damit Farbe nie allein steht */}
        {series.length > 1 && (
          <span className="chart__legend">
            {series.map((s) => (
              <span key={s.key} className="chart__legend-item">
                <span className="chart__swatch" style={{ background: s.color }} aria-hidden />
                {s.label}
                <span className="mono">
                  {latest ? formatNumber(latest[s.key] as number, decimals) : "—"}
                </span>
              </span>
            ))}
          </span>
        )}
      </figcaption>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={CHART.grid} vertical={false} />
            {eclipses.map(([x1, x2]) => (
              <ReferenceArea key={x1} x1={x1} x2={x2} fill={CHART.eclipse} strokeOpacity={0} ifOverflow="hidden" />
            ))}
            <XAxis
              dataKey="x"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(ms: number) => formatTime(ms)}
              stroke={CHART.axis}
              tick={{ fill: CHART.tick, fontSize: 11 }}
              tickLine={false}
              minTickGap={48}
            />
            <YAxis
              width={44}
              domain={yDomain ?? ["auto", "auto"]}
              stroke={CHART.axis}
              tick={{ fill: CHART.tick, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))}
            />
            <Tooltip
              cursor={{ stroke: CHART.tick, strokeWidth: 1 }}
              isAnimationActive={false}
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <div className="tooltip">
                    <div className="tooltip__time mono">{formatTime(label as number, true)} UTC</div>
                    {payload.map((p) => (
                      <div key={String(p.dataKey)} className="tooltip__row">
                        <span className="chart__swatch" style={{ background: p.color }} aria-hidden />
                        <span>{p.name}</span>
                        <span className="mono">
                          {formatNumber(p.value as number, decimals)} {unit}
                        </span>
                      </div>
                    ))}
                    {p0(payload)?.eclipse && <div className="tooltip__note">In eclipse</div>}
                  </div>
                ) : null
              }
            />
            {series.map((s) => (
              <Line
                key={s.key}
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: "var(--surface)", strokeWidth: 2 }}
                type="linear"
                isAnimationActive={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

/** Datenzeile unter dem Mauszeiger (für den Eklipse-Hinweis im Tooltip). */
function p0(payload: ReadonlyArray<{ payload?: unknown }>): ChartRow | undefined {
  return payload[0]?.payload as ChartRow | undefined;
}

/** Fasst aufeinanderfolgende Eklipse-Punkte zu Zeitintervallen [start, ende] zusammen. */
function eclipseIntervals(data: ChartRow[]): [number, number][] {
  const out: [number, number][] = [];
  let start: number | null = null;
  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    if (row.eclipse && start === null) start = row.x;
    if (!row.eclipse && start !== null) {
      out.push([start, row.x]);
      start = null;
    }
  }
  if (start !== null && data.length) out.push([start, data[data.length - 1].x]);
  return out;
}
