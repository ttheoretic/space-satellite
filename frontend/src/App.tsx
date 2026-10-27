// Grundgerüst der Anwendung: Kopfzeile, Navigation und die aktive Seite.

import { useEffect, useState } from "react";
import { api, setApiUser } from "./api";
import { AlarmIndicator } from "./components/AlarmIndicator";
import { ConnectionDot, Header } from "./components/Header";
import { UserSwitcher } from "./components/UserSwitcher";
import { BRAND } from "./brand";
import { useLiveData, useMissionTime } from "./hooks/useLiveData";
import { usePasses } from "./hooks/usePasses";
import { Alarms } from "./pages/Alarms";
import { Dashboard } from "./pages/Dashboard";
import { Limits } from "./pages/Limits";
import { Log } from "./pages/Log";
import { Passes } from "./pages/Passes";
import type { Parameter, User } from "./types";

// Die Seite "Commands" kommt in Schritt 4 dazu.
const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "passes", label: "Passes" },
  { id: "alarms", label: "Alarms" },
  { id: "limits", label: "Limits" },
  { id: "log", label: "Log" },
] as const;
type TabId = (typeof TABS)[number]["id"];

const USER_STORAGE_KEY = "orbitdesk.user";

export default function App() {
  const [tab, setTab] = useState<TabId>("dashboard");
  const [windowMinutes, setWindowMinutes] = useState(180);
  const [params, setParams] = useState<Parameter[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState<string>(() => loadUserId());
  const live = useLiveData(windowMinutes);
  const missionTime = useMissionTime(live.latest, live.status?.clock.speed ?? 1);
  const passes = usePasses(live.status, missionTime, live.reloadKey);
  const user = users.find((u) => u.id === userId);

  useEffect(() => {
    api.parameters().then(setParams).catch(() => {});
    api.users().then(setUsers).catch(() => {});
  }, []);

  // Gewählte Person für alle API-Anfragen setzen und im Browser merken
  setApiUser(userId);
  const changeUser = (id: string) => {
    setUserId(id);
    try {
      localStorage.setItem(USER_STORAGE_KEY, id);
    } catch {
      /* z. B. privates Fenster – dann eben nicht merken */
    }
  };

  // Unbestätigte Alarme auch im Browser-Tab anzeigen: "(2) OrbitDesk"
  const unacked = live.alarms.filter((a) => !a.acknowledged).length;
  useEffect(() => {
    document.title = unacked ? `(${unacked}) ${BRAND.name}` : BRAND.name;
  }, [unacked]);

  // Protokoll neu laden, wenn sich Alarme (z. B. bestätigt) oder Grenzwerte ändern
  const logKey =
    live.alarms.map((a) => `${a.id}:${a.acknowledged}`).join() + live.limits.map((l) => l.updated_at).join();

  return (
    <div className="app">
      <div className="topbar">
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
              {t.id === "alarms" && unacked > 0 && <span className="tabs__badge">{unacked}</span>}
              {t.id === "passes" && live.latest?.contact?.in_contact && (
                <span className="tabs__live" title="Pass in progress">●</span>
              )}
            </button>
          ))}
          <span className="tabs__spacer" />
          <AlarmIndicator alarms={live.alarms} onClick={() => setTab("alarms")} />
          {users.length > 0 && <UserSwitcher users={users} userId={userId} onChange={changeUser} />}
          <ConnectionDot state={live.connection} />
        </nav>
      </div>

      <main className="main">
        {tab === "dashboard" && (
          <Dashboard
            params={params}
            latest={live.latest}
            history={live.history}
            events={live.events}
            limits={live.limits}
            randomFaults={live.status?.simulator.random_faults ?? true}
            passes={passes?.passes ?? []}
            now={missionTime}
            windowMinutes={windowMinutes}
            onWindowChange={setWindowMinutes}
          />
        )}
        {tab === "passes" && <Passes data={passes} now={missionTime} latest={live.latest} user={user} />}
        {tab === "alarms" && <Alarms alarms={live.alarms} latest={live.latest} user={user} />}
        {tab === "limits" && <Limits params={params} limits={live.limits} latest={live.latest} user={user} />}
        {tab === "log" && <Log refreshKey={logKey} />}
      </main>
    </div>
  );
}

function loadUserId(): string {
  try {
    return localStorage.getItem(USER_STORAGE_KEY) ?? "anna";
  } catch {
    return "anna";
  }
}
