// Himmelskarte ("Sky Plot") eines Überflugs, so wie man von der Bodenstation
// nach oben schaut: Mitte = Zenit (senkrecht über der Antenne, 90°),
// äußerer Ring = Horizont (0°). Norden oben, Osten rechts.
// So sieht man auf einen Blick, wohin die Antenne schwenken muss.

import { CHART, STATUS } from "../theme";
import type { Contact, PassTrack } from "../types";

interface Props {
  pass: PassTrack | null;
  /** aktuelle Position, falls der Überflug gerade läuft */
  live?: Contact | null;
  minElevation: number;
}

const SIZE = 260;
const C = SIZE / 2;
const R = SIZE / 2 - 22;

/** Azimut/Elevation → Bildkoordinaten */
function project(az: number, el: number): [number, number] {
  const r = ((90 - Math.max(0, el)) / 90) * R;
  const a = (az * Math.PI) / 180;
  return [C + r * Math.sin(a), C - r * Math.cos(a)];
}

export function SkyPlot({ pass, live, minElevation }: Props) {
  const path = pass?.track.map((p) => project(p.azimuth, p.elevation).join(",")).join(" ");
  const first = pass?.track[0];
  const last = pass?.track[pass.track.length - 1];
  const top = pass?.track.reduce((a, b) => (b.elevation > a.elevation ? b : a), pass.track[0]);

  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="skyplot" role="img" aria-label="Sky plot of the selected pass">
      {/* Elevationsringe 0°, 30°, 60° und Mindestelevation */}
      {[0, 30, 60].map((el) => (
        <g key={el}>
          <circle cx={C} cy={C} r={((90 - el) / 90) * R} fill="none" stroke={el === 0 ? CHART.axis : CHART.grid} />
          {el > 0 && (
            <text x={C + 3} y={C - ((90 - el) / 90) * R + 11} fill={CHART.tick} fontSize={9}>
              {el}°
            </text>
          )}
        </g>
      ))}
      <circle
        cx={C}
        cy={C}
        r={((90 - minElevation) / 90) * R}
        fill="none"
        stroke={CHART.tick}
        strokeDasharray="2 3"
        opacity={0.6}
      />
      <line x1={C - R} x2={C + R} y1={C} y2={C} stroke={CHART.grid} />
      <line x1={C} x2={C} y1={C - R} y2={C + R} stroke={CHART.grid} />
      {(
        [
          ["N", C, C - R - 7],
          ["E", C + R + 9, C + 4],
          ["S", C, C + R + 15],
          ["W", C - R - 9, C + 4],
        ] as const
      ).map(([label, lx, ly]) => (
        <text key={label} x={lx} y={ly} fill={CHART.tick} fontSize={11} fontWeight={700} textAnchor="middle">
          {label}
        </text>
      ))}

      {pass && path && first && last && top && (
        <g>
          <polyline points={path} fill="none" stroke={CHART.series[0]} strokeWidth={2} strokeLinejoin="round" />
          <Marker pt={project(first.azimuth, first.elevation)} label="AOS" />
          <Marker pt={project(last.azimuth, last.elevation)} label="LOS" />
          <Marker pt={project(top.azimuth, top.elevation)} label={`${top.elevation.toFixed(0)}°`} />
        </g>
      )}
      {live && live.in_contact && (
        <g>
          <circle cx={project(live.azimuth, live.elevation)[0]} cy={project(live.azimuth, live.elevation)[1]} r={6}
            fill={STATUS.good} stroke="#15181d" strokeWidth={2} />
        </g>
      )}
      {!pass && (
        <text x={C} y={C} fill={CHART.tick} fontSize={12} textAnchor="middle">
          Select a pass
        </text>
      )}
    </svg>
  );
}

function Marker({ pt, label }: { pt: [number, number]; label: string }) {
  return (
    <g>
      <circle cx={pt[0]} cy={pt[1]} r={4} fill={CHART.series[0]} stroke="#15181d" strokeWidth={2} />
      <text x={pt[0] + 7} y={pt[1] - 6} fill="#e8eaed" fontSize={10} fontWeight={600}>
        {label}
      </text>
    </g>
  );
}
