// Befehlsliste: Befehle anlegen, einem Überflug zuweisen, von einer zweiten
// Person freigeben lassen und während des Überflugs (simuliert) senden.
// Alle Regeln prüft das Backend; die Oberfläche erklärt nur, was gerade geht.

import { useEffect, useState } from "react";
import { api } from "../api";
import { compass, formatDateTime, formatDuration, formatTime } from "../format";
import { currentOrNextPass } from "../hooks/usePasses";
import type { Command, CommandDef, Frame, Pass, User } from "../types";

interface Props {
  commands: Command[];
  passes: Pass[];
  now: number | null;
  latest: Frame | null;
  user: User | undefined;
  stationName: string;
}

const STATUS_LABEL: Record<Command["status"], string> = {
  awaiting_approval: "AWAITING APPROVAL",
  approved: "APPROVED",
  sent: "SENT",
  rejected: "REJECTED",
  cancelled: "CANCELLED",
};
const STATUS_ICON: Record<Command["status"], string> = {
  awaiting_approval: "◷",
  approved: "✓",
  sent: "➜",
  rejected: "✕",
  cancelled: "–",
};

export function Commands({ commands, passes, now, latest, user, stationName }: Props) {
  const [catalog, setCatalog] = useState<CommandDef[]>([]);
  const [error, setError] = useState<string | null>(null);
  const can = (perm: string) => !!user?.permissions.includes(perm);
  const inContact = !!latest?.contact?.in_contact;
  const next = currentOrNextPass(passes, now);
  const upcoming = passes.filter((p) => now === null || Date.parse(p.los) > now);

  useEffect(() => {
    api.commandCatalog().then(setCatalog).catch(() => {});
  }, []);

  /** Führt eine Aktion aus und zeigt Regelverstöße verständlich an. */
  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const open = commands.filter((c) => c.status === "awaiting_approval" || c.status === "approved");
  const done = commands.filter((c) => !open.includes(c));

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Commands</h1>
          <p className="muted small">
            Sending is simulated – there is no radio link. The rules are real: a command needs approval by a{" "}
            <strong>second person</strong> and can only be sent while the spacecraft is in contact during its
            assigned pass.
          </p>
        </div>
      </div>

      <div className={`contact-banner ${inContact ? "contact-banner--live" : ""}`}>
        {inContact && next?.inProgress && now !== null ? (
          <>
            <span className="pill pill--good">● IN CONTACT</span>
            <span>
              Pass <span className="mono">{next.pass.id}</span> over {stationName} · LOS in{" "}
              <span className="mono strong">{formatDuration(Date.parse(next.pass.los) - now)}</span>
            </span>
            <span className="muted">Approved commands for this pass can be sent now.</span>
          </>
        ) : next && now !== null ? (
          <>
            <span className="pill pill--neutral">NO CONTACT</span>
            <span>
              Next pass <span className="mono">{next.pass.id}</span> · AOS in{" "}
              <span className="mono strong">{formatDuration(Date.parse(next.pass.aos) - now)}</span>
            </span>
            <button className="btn btn--ghost btn--small" onClick={() => run(api.jumpToNextPass)}
              title="Demo control: simulate the time until 1 minute before AOS">
              ⏩ Fast-forward to next pass
            </button>
          </>
        ) : (
          <span className="muted">No pass in the next 48 hours.</span>
        )}
      </div>

      <div className="commands-top">
        <section className="panel">
          <h2 className="panel__title">New command</h2>
          <NewCommandForm catalog={catalog} passes={upcoming} canCreate={can("command.create")} run={run} />
        </section>
        <section className="panel">
          <h2 className="panel__title">How a command gets to the spacecraft</h2>
          <ol className="steps">
            <li>
              <strong>Create</strong> – operator or flight director writes the command and picks the pass.
            </li>
            <li>
              <strong>Approve</strong> – a flight director who did <em>not</em> write it checks and approves it
              (four-eyes principle).
            </li>
            <li>
              <strong>Send</strong> – during the pass, while in contact. The spacecraft answers with an ACK.
            </li>
            <li>
              <strong>Log</strong> – every step is recorded with person and time.
            </li>
          </ol>
        </section>
      </div>

      {error && <p className="notice notice--error">{error}</p>}

      <section className="panel">
        <h2 className="panel__title">
          Queue <span className="muted">· {open.length} open</span>
        </h2>
        <CommandTable commands={open} passes={upcoming} user={user} can={can} inContact={inContact}
          now={now} run={run} empty="No open commands." />
      </section>

      <section className="panel">
        <h2 className="panel__title">History</h2>
        <CommandTable commands={done} passes={upcoming} user={user} can={can} inContact={inContact}
          now={now} run={run} empty="No commands sent, rejected or cancelled yet." />
      </section>
    </div>
  );
}

// ------------------------------------------------------------------ Formular

interface FormProps {
  catalog: CommandDef[];
  passes: Pass[];
  canCreate: boolean;
  run: (action: () => Promise<unknown>) => Promise<void>;
}

function NewCommandForm({ catalog, passes, canCreate, run }: FormProps) {
  const [code, setCode] = useState("HEATER_MODE");
  const [args, setArgs] = useState<Record<string, string>>({});
  const [passId, setPassId] = useState<string>("");
  const [comment, setComment] = useState("");
  const def = catalog.find((c) => c.code === code);

  // Bei Befehlswechsel die Argumente auf die ersten Optionen setzen
  useEffect(() => {
    if (def) setArgs(Object.fromEntries(def.args.map((a) => [a.name, a.options[0]])));
  }, [def]);

  // Standard: nächster Überflug
  useEffect(() => {
    if (!passId && passes.length) setPassId(passes[0].id);
    if (passId && !passes.some((p) => p.id === passId)) setPassId(passes[0]?.id ?? "");
  }, [passes, passId]);

  if (!canCreate) {
    return <p className="muted small">Read-only access – switch to an operator or flight director to create commands.</p>;
  }

  const submit = () =>
    run(async () => {
      await api.createCommand({ code, args, pass_id: passId || null, comment });
      setComment("");
    });

  return (
    <div className="cmdform">
      <label className="field">
        <span>Command</span>
        <select value={code} onChange={(e) => setCode(e.target.value)}>
          {catalog.map((c) => (
            <option key={c.code} value={c.code}>
              {c.code} – {c.label}
            </option>
          ))}
        </select>
      </label>
      {def && <p className="muted small cmdform__desc">{def.description}</p>}
      {def?.args.map((a) => (
        <label key={a.name} className="field">
          <span>{a.name}</span>
          <div className="segmented">
            {a.options.map((o) => (
              <button key={o} type="button" className={args[a.name] === o ? "is-active" : ""}
                aria-pressed={args[a.name] === o} onClick={() => setArgs({ ...args, [a.name]: o })}>
                {o}
              </button>
            ))}
          </div>
        </label>
      ))}
      <label className="field">
        <span>Pass</span>
        <PassSelect passes={passes} value={passId} onChange={setPassId} allowNone />
      </label>
      <label className="field">
        <span>Reason / comment</span>
        <input value={comment} maxLength={500} placeholder="Why is this command needed?"
          onChange={(e) => setComment(e.target.value)} />
      </label>
      <div className="cmdform__actions">
        <span className="mono strong">{[code, ...Object.values(args)].join(" ")}</span>
        <button className="btn" onClick={submit}>
          Create command
        </button>
      </div>
    </div>
  );
}

function PassSelect({ passes, value, onChange, allowNone = false }: {
  passes: Pass[]; value: string; onChange: (id: string) => void; allowNone?: boolean;
}) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {allowNone && <option value="">Not scheduled yet</option>}
      {passes.map((p) => (
        <option key={p.id} value={p.id}>
          {formatDateTime(Date.parse(p.aos)).slice(5, 16)} UTC · max {p.max_elevation.toFixed(0)}° ·{" "}
          {compass(p.aos_azimuth)}→{compass(p.los_azimuth)}
        </option>
      ))}
    </select>
  );
}

// ------------------------------------------------------------------ Tabelle

interface TableProps {
  commands: Command[];
  passes: Pass[];
  user: User | undefined;
  can: (perm: string) => boolean;
  inContact: boolean;
  now: number | null;
  run: (action: () => Promise<unknown>) => Promise<void>;
  empty: string;
}

function CommandTable({ commands, passes, user, can, inContact, now, run, empty }: TableProps) {
  if (!commands.length) return <p className="muted small">{empty}</p>;
  return (
    <table className="table cmdtable">
      <thead>
        <tr>
          <th>#</th>
          <th>Command</th>
          <th>Pass</th>
          <th>Status</th>
          <th>Created</th>
          <th>Approved / rejected</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {commands.map((c) => (
          <tr key={c.id} className={c.status === "approved" && passState(c, now) === "in_progress" ? "row--ready" : ""}>
            <td className="mono muted">{c.id}</td>
            <td>
              <div className="mono strong">{c.text}</div>
              {c.comment && <div className="muted small">{c.comment}</div>}
              {c.result && <div className="small cmd-result">✓ {c.result}</div>}
              {c.reject_reason && <div className="small cmd-reject">Reason: {c.reject_reason}</div>}
            </td>
            <td>
              <PassCell c={c} now={now} />
            </td>
            <td>
              <span className={`cstatus cstatus--${c.status}`}>
                <span aria-hidden>{STATUS_ICON[c.status]}</span> {STATUS_LABEL[c.status]}
              </span>
            </td>
            <td className="small">
              {c.created_by}
              <div className="muted mono">{formatTime(Date.parse(c.created_at), true)}</div>
            </td>
            <td className="small">
              {c.decided_by ?? <span className="muted">—</span>}
              {c.decided_at && <div className="muted mono">{formatTime(Date.parse(c.decided_at), true)}</div>}
              {c.sent_by && (
                <div className="muted">
                  sent by {c.sent_by} {c.sent_at && formatTime(Date.parse(c.sent_at), true)}
                </div>
              )}
            </td>
            <td>
              <Actions c={c} passes={passes} user={user} can={can} inContact={inContact} now={now} run={run} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Zustand des zugewiesenen Überflugs – laufend aus der Missionszeit berechnet. */
function passState(c: Command, now: number | null): "upcoming" | "in_progress" | "over" | null {
  if (!c.pass_aos || !c.pass_los || now === null) return c.pass_state;
  if (now < Date.parse(c.pass_aos)) return "upcoming";
  return now <= Date.parse(c.pass_los) ? "in_progress" : "over";
}

function PassCell({ c, now }: { c: Command; now: number | null }) {
  if (!c.pass_id || !c.pass_aos) return <span className="muted small">not scheduled</span>;
  const aos = Date.parse(c.pass_aos);
  const state = passState(c, now);
  return (
    <div className="small">
      <div className="mono">{formatDateTime(aos).slice(5, 16)} UTC</div>
      {c.status !== "sent" && c.status !== "cancelled" && c.status !== "rejected" && (
        <>
          {state === "in_progress" && <span className="pill pill--good">● IN CONTACT</span>}
          {state === "upcoming" && now !== null && (
            <span className="muted">AOS in {formatDuration(aos - now)}</span>
          )}
          {state === "over" && <span className="cmd-missed">pass missed – reschedule</span>}
        </>
      )}
    </div>
  );
}

function Actions({ c, passes, user, can, inContact, now, run }: {
  c: Command; passes: Pass[]; user: User | undefined; can: (p: string) => boolean;
  inContact: boolean; now: number | null; run: (action: () => Promise<unknown>) => Promise<void>;
}) {
  if (c.status !== "awaiting_approval" && c.status !== "approved") return null;
  const isAuthor = user?.name === c.created_by;

  // Warum kann (noch) nicht gesendet werden?
  let sendBlocked: string | null = null;
  if (c.status !== "approved") sendBlocked = "Needs approval first";
  else if (!c.pass_id) sendBlocked = "Assign a pass first";
  else if (passState(c, now) !== "in_progress" || !inContact) sendBlocked = "Only possible during the assigned pass";
  else if (!can("command.send")) sendBlocked = `${user?.name} may not send commands`;

  let approveBlocked: string | null = null;
  if (!can("command.approve")) approveBlocked = "Only a flight director can approve";
  else if (isAuthor) approveBlocked = "Four-eyes principle: approval by a second person";

  return (
    <div className="cmd-actions">
      {c.status === "awaiting_approval" && (
        <>
          <button className="btn btn--small" disabled={!!approveBlocked} title={approveBlocked ?? undefined}
            onClick={() => run(() => api.approveCommand(c.id))}>
            Approve
          </button>
          {can("command.approve") && !isAuthor && (
            <button className="btn btn--small btn--ghost"
              onClick={() => {
                const reason = window.prompt(`Reject command #${c.id} (${c.text}) – reason:`);
                if (reason !== null) run(() => api.rejectCommand(c.id, reason));
              }}>
              Reject
            </button>
          )}
        </>
      )}
      {c.status === "approved" && (
        <button className={`btn btn--small ${sendBlocked ? "" : "btn--send"}`} disabled={!!sendBlocked}
          title={sendBlocked ?? "Uplink the command now"} onClick={() => run(() => api.sendCommand(c.id))}>
          ➜ Send
        </button>
      )}
      {can("command.schedule") && (
        <select className="cmd-actions__pass" value="" aria-label="Change pass"
          onChange={(e) => e.target.value && run(() => api.scheduleCommand(c.id, e.target.value))}>
          <option value="">{c.pass_id ? "Change pass…" : "Assign pass…"}</option>
          {passes.map((p) => (
            <option key={p.id} value={p.id}>
              {formatDateTime(Date.parse(p.aos)).slice(5, 16)} UTC · max {p.max_elevation.toFixed(0)}°
            </option>
          ))}
        </select>
      )}
      {can("command.create") && (
        <button className="btn btn--small btn--ghost" onClick={() => run(() => api.cancelCommand(c.id))}>
          Cancel
        </button>
      )}
    </div>
  );
}
