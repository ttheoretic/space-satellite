// Zeitleiste der nächsten 48 Stunden: Jeder Überflug ist ein Balken.
// Breite = Dauer, Höhe = maximale Elevation (höher = besserer Überflug).

import { useEffect, useRef, useState } from "react";
import { formatDuration, formatTime } from "../format";
import { CHART, STATUS } from "../theme";
import type { Pass } from "../types";

interface Props {
  passes: Pass[];
  start: number; // ms
  hours: number;
  now: number | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const HEIGHT = 130;
const TOP = 22; // Platz für Datumszeile
const BOTTOM = 22; // Platz für Uhrzeiten
const PLOT_H = HEIGHT - TOP - BOTTOM;
const MIN_BAR_W = 6;

export function PassTimeline({ passes, start, hours, now, selectedId, onSelect }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const width = useWidth(ref);
  const [hover, setHover] = useState<{ pass: Pass; x: number } | null>(null);

  const end = start + hours * 3600_000;
  const x = (ms: number) => ((ms - start) / (end - start)) * width;
  const barH = (el: number) => Math.max(6, (el / 90) * PLOT_H);

  // Achsenbeschriftung alle 3 Stunden, Tageswechsel hervorgehoben
  const ticks: number[] = [];
  const first = Math.ceil(start / (3 * 3600_000)) * 3 * 3600_000;
  for (let t = first; t <= end; t += 3 * 3600_000) ticks.push(t);

  return (
    <div className="timeline" ref={ref}>
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label="Pass timeline, next 48 hours">
          {/* Gitter und Uhrzeiten */}
          {ticks.map((t) => {
            const midnight = new Date(t).getUTCHours() === 0;
            return (
              <g key={t}>
                <line x1={x(t)} x2={x(t)} y1={TOP} y2={TOP + PLOT_H} stroke={midnight ? CHART.axis : CHART.grid} />
                <text x={x(t)} y={HEIGHT - 6} fill={CHART.tick} fontSize={11} textAnchor="middle">
                  {formatTime(t)}
                </text>
                {midnight && (
                  <text x={x(t) + 4} y={14} fill={CHART.tick} fontSize={11}>
                    {new Date(t).toISOString().slice(0, 10)}
                  </text>
                )}
              </g>
            );
          })}
          <line x1={0} x2={width} y1={TOP + PLOT_H} y2={TOP + PLOT_H} stroke={CHART.axis} />

          {/* Überflüge */}
          {passes.map((p) => {
            const a = Date.parse(p.aos);
            const l = Date.parse(p.los);
            const inProgress = now !== null && a <= now && now <= l;
            const selected = p.id === selectedId;
            const w = Math.max(MIN_BAR_W, x(l) - x(a));
            const h = barH(p.max_elevation);
            const bx = x(a) - (w - (x(l) - x(a))) / 2;
            return (
              <g
                key={p.id}
                className="timeline__pass"
                onClick={() => onSelect(p.id)}
                onMouseEnter={() => setHover({ pass: p, x: bx + w / 2 })}
                onMouseLeave={() => setHover(null)}
              >
                {/* unsichtbare, größere Klickfläche */}
                <rect x={bx - 6} y={TOP} width={w + 12} height={PLOT_H} fill="transparent" />
                <rect
                  x={bx}
                  y={TOP + PLOT_H - h}
                  width={w}
                  height={h}
                  rx={2}
                  fill={inProgress ? STATUS.good : CHART.series[0]}
                  opacity={p.max_elevation < 15 && !selected ? 0.55 : 1}
                  stroke={selected ? "#ffffff" : "none"}
                  strokeWidth={selected ? 2 : 0}
                />
              </g>
            );
          })}

          {/* Jetzt-Linie */}
          {now !== null && now >= start && now <= end && (
            <g>
              <line x1={x(now)} x2={x(now)} y1={TOP - 4} y2={TOP + PLOT_H} stroke="#ffffff" strokeWidth={1.5} />
              <text x={x(now) + 4} y={TOP + 8} fill="#ffffff" fontSize={10} fontWeight={700}>
                NOW
              </text>
            </g>
          )}
        </svg>
      )}
      {hover && (
        <div className="tooltip timeline__tooltip" style={{ left: Math.min(Math.max(hover.x, 90), width - 90) }}>
          <div className="tooltip__time mono">
            {formatTime(Date.parse(hover.pass.aos), true)} – {formatTime(Date.parse(hover.pass.los), true)} UTC
          </div>
          <div>
            Max elevation <span className="mono">{hover.pass.max_elevation.toFixed(1)}°</span>
          </div>
          <div>
            Duration <span className="mono">{formatDuration(hover.pass.duration_s * 1000)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

/** Breite eines Elements beobachten (für responsives SVG). */
function useWidth(ref: React.RefObject<HTMLElement>): number {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const obs = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, [ref]);
  return width;
}
