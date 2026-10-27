// Grundgerüst der Anwendung: Kopfzeile, Navigation und die aktive Seite.

import { useEffect, useState } from "react";
import { api } from "./api";
import { ConnectionDot, Header } from "./components/Header";
import { useLiveData, useMissionTime } from "./hooks/useLiveData";
import { Dashboard } from "./pages/Dashboard";
import type { Parameter } from "./types";

// Weitere Seiten (Alarms, Passes, Commands) kommen in den nächsten Schritten dazu.
const TABS = [{ id: "dashboard", label: "Dashboard" }] as const;
type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("dashboard");
  const [windowMinutes, setWindowMinutes] = useState(180);
  const [params, setParams] = useState<Parameter[]>([]);
  const live = useLiveData(windowMinutes);
  const missionTime = useMissionTime(live.latest, live.status?.clock.speed ?? 1);

  useEffect(() => {
    api.parameters().then(setParams).catch(() => {});
  }, []);

  return (
    <div className="app">
      <Header status={live.status} missionTime={missionTime} />
      <nav className="tabs" aria-label="Main">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tabs__tab ${tab === t.id ? "is-active" : ""}`}
            aria-current={tab === t.id ? "page" : undefined}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
        <span className="tabs__spacer" />
        <ConnectionDot state={live.connection} />
      </nav>
      <main className="main">
        {tab === "dashboard" && (
          <Dashboard
            params={params}
            latest={live.latest}
            history={live.history}
            events={live.events}
            windowMinutes={windowMinutes}
            onWindowChange={setWindowMinutes}
          />
        )}
      </main>
    </div>
  );
}
