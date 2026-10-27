// Überflugplanung: nächster Überflug mit Countdown, Bodenstation,
// Zeitleiste der nächsten 48 h, Liste aller Überflüge und Himmelskarte.

import { useEffect, useState } from "react";
import { api } from "../api";
import { PassTimeline } from "../components/PassTimeline";
import { SkyPlot } from "../components/SkyPlot";
import { StationForm } from "../components/StationForm";
import { compass, formatDateTime, formatDuration, formatTime } from "../format";
import { currentOrNextPass } from "../hooks/usePasses";
import type { Frame, PassesResponse, PassTrack, User } from "../types";

interface Props {
  data: PassesResponse | null;
  now: number | null;
  latest: Frame | null;
  user: User | undefined;
}

export function Passes({ data, now, latest, user }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [track, setTrack] = useState<PassTrack | null>(null);
  const [jumpBusy, setJumpBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passes = data?.passes ?? [];
  const next = currentOrNextPass(passes, now);
  // Ohne Auswahl: laufenden bzw. nächsten Überflug zeigen
  const shownId = selectedId && passes.some((p) => p.id === selectedId) ? selectedId : next?.pass.id ?? null;

  useEffect(() => {
    if (!shownId) return setTrack(null);
    let cancelled = false;
    api.pass(shownId).then((t) => !cancelled && setTrack(t)).catch(() => !cancelled && setTrack(null));
    return () => {
      cancelled = true;
    };
  }, [shownId]);

  const jump = async () => {
    setError(null);
    setJumpBusy(true);
    try {
      await api.jumpToNextPass();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setJumpBusy(false);
    }
  };

  if (!data) return <p className="muted">Calculating passes…</p>;
  const station = data.station;
  const canEdit = !!user?.permissions.includes("station.edit");
  const contact = latest?.contact;
  // Zeitleiste beginnt zur vollen Stunde vor "jetzt"
  const start = now !== null ? Math.floor(now / 3600_000) * 3600_000 : Date.parse(data.generated_at);

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Pass Planning</h1>
          <p className="muted small">
            Passes of the spacecraft over {station.name} in the next {data.hours} hours (mission time), computed
            from the current TLE with Skyfield. A pass starts at <strong>AOS</strong> (acquisition of signal)
            when the spacecraft rises above {station.min_elevation}° elevation and ends at <strong>LOS</strong>{" "}
            (loss of signal).
          </p>
        </div>
      </div>
      {data.tle_source === "fallback" && (
        <p className="notice notice--warn">
          Passes are computed from the built-in fallback TLE, which only approximates the real orbit. Real pass
          times may differ.
        </p>
      )}

      <div className="passes-top">
        <section className={`panel next-pass ${next?.inProgress ? "next-pass--live" : ""}`}>
          <h2 className="panel__title">{next?.inProgress ? "Pass in progress" : "Next pass"}</h2>
          {next && now !== null ? (
            <>
              <div className="next-pass__countdown">
                {next.inProgress ? (
                  <>
                    <span className="pill pill--good">● IN CONTACT</span>
                    <span className="mono">LOS in {formatDuration(Date.parse(next.pass.los) - now)}</span>
                  </>
                ) : (
                  <>
                    <span className="muted">AOS in</span>
                    <span className="mono">{formatDuration(Date.parse(next.pass.aos) - now)}</span>
                  </>
                )}
              </div>
              <dl className="kv next-pass__kv">
                <dt>AOS</dt>
                <dd className="mono">
                  {formatDateTime(Date.parse(next.pass.aos))} UTC · {compass(next.pass.aos_azimuth)}
                </dd>
                <dt>LOS</dt>
                <dd className="mono">
                  {formatDateTime(Date.parse(next.pass.los))} UTC · {compass(next.pass.los_azimuth)}
                </dd>
                <dt>Max elevation</dt>
                <dd className="mono">{next.pass.max_elevation.toFixed(1)}°</dd>
                <dt>Duration</dt>
                <dd className="mono">{formatDuration(next.pass.duration_s * 1000)}</dd>
                {next.inProgress && contact && (
                  <>
                    <dt>Now</dt>
                    <dd className="mono">
                      El {contact.elevation.toFixed(1)}° · Az {contact.azimuth.toFixed(0)}° · {contact.range_km.toFixed(0)} km
                    </dd>
                  </>
                )}
              </dl>
              {!next.inProgress && (
                <button className="btn btn--ghost btn--small" onClick={jump} disabled={jumpBusy}
                  title="Demo control: simulate the time until 1 minute before AOS">
                  {jumpBusy ? "Fast-forwarding…" : "⏩ Fast-forward to next pass"}
                </button>
              )}
              {error && <p className="notice notice--error">{error}</p>}
            </>
          ) : (
            <p className="muted">No pass in the next {data.hours} hours.</p>
          )}
        </section>

        <section className="panel">
          <h2 className="panel__title">Ground station</h2>
          <StationForm station={station} canEdit={canEdit} />
        </section>
      </div>

      <section className="panel">
        <h2 className="panel__title">
          Timeline <span className="muted">· bar height = max elevation · click to select</span>
        </h2>
        <PassTimeline passes={passes} start={start} hours={data.hours} now={now} selectedId={shownId}
          onSelect={setSelectedId} />
      </section>

      <div className="passes-bottom">
        <section className="panel">
          <h2 className="panel__title">
            Passes <span className="muted">· {passes.length} in {data.hours} h</span>
          </h2>
          <table className="table table--compact table--select">
            <thead>
              <tr>
                <th>Pass</th>
                <th>AOS (UTC)</th>
                <th>LOS (UTC)</th>
                <th className="num">Duration</th>
                <th>Max elevation</th>
                <th>Direction</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {passes.map((p) => {
                const live = now !== null && Date.parse(p.aos) <= now && now <= Date.parse(p.los);
                return (
                  <tr key={p.id} className={p.id === shownId ? "is-selected" : ""} onClick={() => setSelectedId(p.id)}>
                    <td className="mono small muted">{p.id}</td>
                    <td className="mono">{formatDateTime(Date.parse(p.aos))}</td>
                    <td className="mono">{formatTime(Date.parse(p.los), true)}</td>
                    <td className="num mono">{formatDuration(p.duration_s * 1000)}</td>
                    <td>
                      <span className="elbar" aria-hidden>
                        <span style={{ width: `${(p.max_elevation / 90) * 100}%` }} />
                      </span>
                      <span className="mono">{p.max_elevation.toFixed(1)}°</span>
                    </td>
                    <td className="mono small">
                      {compass(p.aos_azimuth)} → {compass(p.los_azimuth)}
                    </td>
                    <td>{live && <span className="pill pill--good">● LIVE</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <h2 className="panel__title">
            Sky plot <span className="muted">{track ? `· ${track.id}` : ""}</span>
          </h2>
          <SkyPlot pass={track} live={track && contact?.in_contact ? contact : null} minElevation={station.min_elevation} />
          <p className="muted small">
            View from the antenna: centre = straight up (90°), outer ring = horizon, north at the top. The dashed
            ring is the minimum elevation.
          </p>
        </section>
      </div>
    </div>
  );
}
