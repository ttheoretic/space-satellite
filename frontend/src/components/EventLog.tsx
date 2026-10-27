// Liste der Bordereignisse (Eklipse-Ein-/Austritt, Moduswechsel, Fehler …).

import { formatDateTime } from "../format";
import type { SpacecraftEvent } from "../types";

export function EventLog({ events }: { events: SpacecraftEvent[] }) {
  return (
    <ul className="eventlog">
      {events.length === 0 && <li className="muted">No events yet.</li>}
      {events.slice(0, 60).map((e, i) => (
        <li key={`${e.t}-${i}`} className={`eventlog__item eventlog__item--${e.level}`}>
          <span className="mono muted">{e.t ? formatDateTime(Date.parse(e.t)) : ""}</span>
          <span className="eventlog__icon" aria-label={e.level}>
            {e.level === "warning" ? "▲" : "•"}
          </span>
          <span>{e.text}</span>
        </li>
      ))}
    </ul>
  );
}
