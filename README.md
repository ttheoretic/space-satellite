# OrbitDesk – Leitstand für kleine Satellitenmissionen (Prototyp)

OrbitDesk ist ein schlanker Leitstand im Browser für CubeSat-Teams und junge
New-Space-Startups. Dieser Prototyp dient als Demo für Kundengespräche.

> **Wichtig:** Alle Telemetrie in OrbitDesk ist **simuliert**. Die Bahn stammt
> aus echten TLE-Bahndaten von SONATE-2, Messwerte wie Batteriespannung oder
> Temperaturen erzeugt aber ein Simulator. Die Kopfzeile zeigt deshalb dauerhaft
> **„SIMULATED TELEMETRY“**.

**Stand: Prototyp vollständig (Schritt 4 von 4)** – Simulator, Live-Dashboard,
Grenzwerte & Alarme, Überflugplanung und Befehlsliste mit Vier-Augen-Freigabe,
dazu Demo-Personen mit Rollen und ein lückenloses Betriebsprotokoll.

---

## Inhalt

1. [Schnellstart mit Docker](#schnellstart-mit-docker)
2. [Start ohne Docker (macOS, Linux, Windows)](#start-ohne-docker)
3. [Was man sieht – kurze Tour](#was-man-sieht--kurze-tour)
4. [Demo-Drehbuch](#demo-drehbuch)
5. [Konfiguration](#konfiguration)
6. [Architektur und Ordnerstruktur](#architektur-und-ordnerstruktur)
7. [Tests](#tests)
8. [Fachbegriffe](#fachbegriffe)
9. [Grenzen des Prototyps](#grenzen-des-prototyps)

---

## Schnellstart mit Docker

Voraussetzung: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(macOS/Windows) bzw. Docker Engine mit Compose-Plugin (Linux).

```bash
docker compose up --build
```

Danach im Browser (Chrome oder Firefox) öffnen: **http://localhost:8080**

Beenden mit `Strg+C`. Daten (Datenbank, TLE-Cache) liegen in einem
Docker-Volume und bleiben erhalten. Komplett zurücksetzen:
`docker compose down -v`.

---

## Start ohne Docker

Falls Docker Desktop auf deinem Rechner nicht läuft (z. B. älteres macOS),
startest du Backend und Frontend direkt.

### Voraussetzungen

| Werkzeug | Version | Prüfen mit | Bezugsquelle |
|---|---|---|---|
| Python | **3.10 oder neuer** | `python3 --version` | [python.org/downloads/macos](https://www.python.org/downloads/macos/) (Installer) oder `brew install python@3.12` |
| Node.js | **18 oder neuer** | `node --version` | [nodejs.org](https://nodejs.org/) (LTS-Installer) oder `brew install node@18` |

Hinweise für ältere Macs:
- Node.js 18 und 20 laufen ab macOS 10.15 (Catalina). Ab Node.js 22 ist
  macOS 11 nötig – nimm daher im Zweifel **Node.js 18 oder 20**.
- Die aktuellen Python-Installer von python.org laufen ab macOS 10.13.
- Falls Node.js gar nicht installierbar ist: Das Frontend lässt sich auf einem
  anderen Rechner bauen (`npm run build`) und der Ordner `frontend/dist`
  herüberkopieren. Zum Betrieb braucht man dann nur noch Python
  (siehe Variante A).

### Variante A – Demo-Modus (empfohlen für Vorführungen)

Das Frontend wird einmal gebaut, danach läuft nur **ein** Prozess, der alles
ausliefert. Alle Befehle im Terminal, im Projektordner:

```bash
# 1) Frontend bauen (einmalig bzw. nach Änderungen am Frontend)
cd frontend
npm install
npm run build
cd ..

# 2) Python-Umgebung einrichten (einmalig)
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3) Starten
uvicorn app.main:app --port 8080
```

Öffnen: **http://localhost:8080**

Bei späteren Starts genügen:
`cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8080`

### Variante B – Entwicklungsmodus (Code ändern, sofort sehen)

Zwei Terminals:

```bash
# Terminal 1 – Backend mit automatischem Neuladen bei Code-Änderungen
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 – Frontend-Entwicklungsserver
cd frontend
npm run dev
```

Öffnen: **http://localhost:5173**. Der Entwicklungsserver leitet API- und
WebSocket-Anfragen automatisch an das Backend auf Port 8000 weiter.

Die interaktive API-Dokumentation (von FastAPI automatisch erzeugt) findest du
unter http://localhost:8000/docs bzw. http://localhost:8080/docs.

---

## Was man sieht – kurze Tour

**Kopfzeile** (bleibt immer sichtbar)
- **OrbitDesk · SONATE-2 · NORAD 59112** – Produkt und Satellit
- **SIMULATED TELEMETRY** – Hinweis, dass die Messwerte simuliert sind
- **Mission Time** – Missionszeit in UTC (läuft im Zeitraffer schneller)
- **1× / 10× / 60×** – Zeitraffer. Bei 60× vergeht pro echter Sekunde eine
  Minute; ein ganzer Orbit (~95 min) dauert dann gut 1,5 Minuten
- **TLE-Anzeige** – welche Bahndaten verwendet werden und wie alt sie sind
  (Klick öffnet Details und „Reload from CelesTrak“):

  | Anzeige | Bedeutung |
  |---|---|
  | `TLE LIVE · 1.2 d` | frisch von CelesTrak geladen |
  | `TLE CACHED · 3.0 d` | zuletzt erfolgreich geladene TLE (CelesTrak gerade nicht erreichbar) |
  | `⚠ TLE FALLBACK · …` | eingebaute Ersatz-TLE – nur eine **Annäherung** an die echte Bahn |
  | `⚠` und gelb | TLE ist **14 Tage oder älter** (oder Ersatz-TLE) |

  Das Alter wird relativ zur **Missionszeit** berechnet: Spult man im
  Zeitraffer einen Tag vor, wird die TLE auch einen Tag „älter“ – genau so
  wächst in der Realität die Ungenauigkeit der Vorhersage.

**Navigationsleiste** – Seiten *Dashboard*, *Passes*, *Commands*, *Alarms*,
*Limits*, *Log* (grüner Punkt bei *Passes* = Überflug läuft gerade, blaue Zahl
bei *Commands* = Befehle warten auf Freigabe); rechts:
- **Alarmanzeige**: `✓ NO ALARMS`, gelb (Warnung) oder rot (kritisch) mit Anzahl
  aktiver und unbestätigter Alarme. Unbestätigte Alarme pulsieren; ein Klick
  öffnet die Alarmliste. Auch der Browser-Tab zeigt die Anzahl: „(2) OrbitDesk“.
- **Personenauswahl** (Demo ohne Login):

  | Person | Rolle | Darf |
  |---|---|---|
  | Anna | Operator | Alarme bestätigen, Grenzwerte und Bodenstation ändern, Befehle anlegen, einplanen und senden |
  | Ben | Flight Director | wie Operator, zusätzlich Befehle freigeben oder ablehnen |
  | Clara | Engineer | nur lesen |

  Die Rechte prüft das **Backend** bei jeder Aktion – nicht nur die Oberfläche.
- **Verbindungsstatus** zum Server (`LIVE` / `RECONNECTING`). Bricht die
  Verbindung ab, verbindet sich die Seite selbst neu.

**Dashboard**
- **Statusleiste:** Betriebsmodus (NOMINAL/SAFE), Sonne oder Erdschatten,
  Batterieheizung, **Funkkontakt** (`IN CONTACT · EL 34°` oder „Next AOS in …“),
  Position über der Erde und Bahnhöhe
- **Power / Thermal / Attitude:** aktuelle Messwerte je Subsystem. Verletzt ein
  Wert eine Grenze, färbt sich die Kachel **gelb (▲ WARNING)** oder
  **rot (◆ CRITICAL)** – immer mit Symbol und Text, nie nur über die Farbe. Mit der
  Maus über einer Kachel erscheinen Erklärung und Grenzwerte
- **Trends:** Verlaufsdiagramme für 30 min, 3 h oder 12 h. Grau hinterlegte
  Bereiche = Eklipse, gestrichelte Linien = Grenzwerte (gelb/rot). So sieht man Ursache und Wirkung: Eintritt in den Schatten
  → Solarleistung fällt auf 0 → Ladezustand sinkt → Panels kühlen ab
- **Onboard Events:** Ereignisse an Bord (Eklipse, Moduswechsel, Fehler)
- **Simulation (Demo controls):** Fehler gezielt auslösen (*Trigger*), alle
  Fehler beheben, Zufallsfehler ein/aus, Demo zurücksetzen. Bei aktivem Fehler
  steht dabei, wie man ihn im echten Betrieb beheben würde.

**Passes** – Überflugplanung für die Bodenstation (Standard: TU Berlin):
- **Next pass / Pass in progress:** Countdown bis AOS bzw. LOS, Richtung,
  maximale Elevation, Dauer; während des Überflugs live Elevation, Azimut und
  Entfernung. *Fast-forward to next pass* (Demo) spult bis 1 Minute vor AOS vor –
  die übersprungene Zeit wird im Schnelldurchlauf simuliert, Verlauf und Alarme
  bleiben lückenlos.
- **Ground station:** Name, Position, Höhe und Mindestelevation (Standard 5°),
  mit Vorlagen (TU Berlin, Uni Würzburg, Uni Stuttgart). Ändern dürfen Operator
  und Flight Director; die Änderung steht im Protokoll.
- **Timeline:** die nächsten 48 h; jeder Balken ein Überflug, Höhe = maximale
  Elevation. Grün = läuft gerade, Klick = auswählen.
- **Passes:** Liste mit AOS, LOS, Dauer, maximaler Elevation und Richtung.
- **Sky plot:** Bahn des gewählten Überflugs am Himmel, wie von der Antenne aus
  gesehen (Mitte = senkrecht oben, Rand = Horizont, Norden oben). Während des
  Überflugs zeigt ein grüner Punkt die aktuelle Position.

Die Überflüge werden mit Skyfield aus der TLE berechnet (`find_events`).
Mit der Ersatz-TLE weist ein Hinweis darauf hin, dass die Zeiten nur angenähert
sind.

**Commands** – Befehlsliste. Das Senden ist simuliert (keine Funkverbindung),
die Regeln sind echt:

| Schritt | Wer | Regel |
|---|---|---|
| 1. Anlegen | Operator oder Flight Director | Befehl aus dem Katalog wählen, Argument, Überflug und Begründung angeben. Der Inhalt ist danach nicht mehr änderbar. |
| 2. Einplanen | Operator oder Flight Director | Überflug zuweisen oder ändern („Change pass…“), solange nicht gesendet. Verpasste Überflüge werden markiert. |
| 3. Freigeben / Ablehnen | Flight Director | **Vier-Augen-Prinzip:** nicht die Person, die den Befehl angelegt hat. Ablehnen nur mit Begründung. |
| 4. Senden | Operator oder Flight Director | Nur freigegeben **und** während des zugewiesenen Überflugs mit Kontakt. Der Satellit antwortet mit einem ACK. |
| – Abbrechen | Operator oder Flight Director | jederzeit vor dem Senden |

Befehlskatalog: `PING` (Verbindungstest), `SET_MODE NOMINAL|SAFE`,
`HEATER_MODE AUTO|ON|OFF`, `RESET_ADCS`. Gesendete Befehle wirken auf den
Simulator – z. B. schaltet `HEATER_MODE ON` nach einem Thermostat-Ausfall die
Heizung über den Ersatz-Schaltkreis ein, `RESET_ADCS` beendet das Taumeln,
`SET_MODE SAFE` schaltet die Nutzlast ab und beendet einen Latch-up.
Oben zeigt ein Banner, ob gerade Kontakt besteht und wann der nächste
Überflug beginnt (mit *Fast-forward*). Jede Aktion steht im *Log*.

**Alarms** – offene Alarme mit Stufe, Zustand (`ACTIVE` / `BACK TO NORMAL`),
Wert beim Auslösen und aktuell, verletzter Grenze und Zeit. Ein Alarm bleibt in
der Liste, bis sein Wert wieder gut ist **und** jemand ihn bestätigt hat – so
geht auch ein kurzer Ausreißer nicht unbemerkt verloren. Darunter das Archiv.

Regeln der Alarmlogik:
- Verschlechterung wird sofort gemeldet; eine Eskalation von Warnung auf
  kritisch muss **erneut bestätigt** werden.
- **Hysterese:** Ein Alarm klingt erst ab, wenn der Wert ein kleines Stück (2 %
  der Spanne zwischen den Grenzen) zurück im guten Bereich ist. Sonst würde ein
  rauschender Wert an der Grenze ständig neue Alarme erzeugen („Alarmflattern“).

**Limits** – Grenzwert-Editor: pro Messwert kritisch/Warnung unten und oben,
leeres Feld = keine Grenze, Haken = Grenzwerte aktiv. *Default* stellt die
Standardwerte wieder her. Das Backend prüft die Reihenfolge
(kritisch unten < Warnung unten < Warnung oben < kritisch oben).

**Log** – Betriebsprotokoll: jede Aktion (Befehl angelegt/freigegeben/gesendet,
Alarm bestätigt, Grenzwert oder Bodenstation geändert) mit Person, Missionszeit
und echter Uhrzeit, inklusive Antwort des Satelliten.

Beim allerersten Start werden die letzten 3 Stunden „vorsimuliert“, damit die
Diagramme sofort Kurven zeigen.

---

## Demo-Drehbuch

Die Geschichte: **Ein Fehler an Bord wird erkannt, das Team plant einen
Befehl, eine zweite Person gibt ihn frei, im nächsten Überflug wird er
gesendet – und die Telemetrie zeigt die Erholung.** Dauer ca. 8 Minuten.

Vorbereitung: *Simulation → Reset demo*, „Random faults“ ausschalten, als
**Anna (Operator)** angemeldet sein.

1. **Überblick (1 min):** Dashboard zeigen. Auf **SIMULATED TELEMETRY** und die
   **TLE-Anzeige** hinweisen: „Die Bahn ist die echte von SONATE-2, aktuell von
   CelesTrak – die Messwerte simuliert.“ Diagramm *State of Charge* erklären:
   Sägezahn = Laden in der Sonne, Entladen im Erdschatten (graue Bereiche).
2. **Fehler (1 min):** Unter *Simulation* „Battery heater thermostat failure“
   auslösen und auf **60×** stellen. In der nächsten Eklipse kühlt die Batterie
   ab: Kachel *Battery Temp* wird gelb, dann rot, die Alarmanzeige pulsiert.
   Zurück auf **1×**.
3. **Alarm bestätigen (1 min):** Auf **Clara (Engineer)** wechseln → *Alarms*:
   Bestätigen ist gesperrt (nur Lesezugriff). Zurück zu **Anna** und bestätigen.
4. **Wann können wir funken? (1 min):** *Passes* öffnen – Countdown, Zeitleiste
   der nächsten 48 h, Himmelskarte. „Nur während eines Überflugs besteht
   Funkkontakt.“
5. **Befehl anlegen (1 min):** *Commands* → `HEATER_MODE` / `ON`, nächsten
   Überflug wählen, Begründung „Thermostat failed – use backup circuit“,
   *Create command*. Zeigen: Anna kann ihren eigenen Befehl **nicht** freigeben.
6. **Freigabe (30 s):** Auf **Ben (Flight Director)** wechseln → *Approve*.
7. **Senden (1 min):** Zurück zu **Anna**. *Fast-forward to next pass*, dann
   **10×**. Bei Kontaktbeginn wird die Zeile grün → **Send**. Antwort des
   Satelliten: „ACK – battery heater ON“. Wieder **1×**.
8. **Ergebnis (1 min):** Dashboard: Heizung `ON · manual`, die
   Batterietemperatur steigt, der Alarm geht auf `BACK TO NORMAL`.
   *Log* zeigt die ganze Kette: angelegt (Anna), freigegeben (Ben), gesendet
   (Anna), mit Zeiten und Antwort.

Kürzere Variante: „Reaction wheel anomaly“ auslösen – der Satellit taumelt
sofort sichtbar (*Pointing Error*, *Angular Rate*); behoben wird er mit dem
Befehl `RESET_ADCS`.

---

## Konfiguration

Alle Einstellungen haben Standardwerte und lassen sich über
Umgebungsvariablen ändern – in `docker-compose.yml` unter `environment:` oder
beim direkten Start, z. B.:

```bash
ORBITDESK_STATION_LAT=48.15 ORBITDESK_STATION_LON=11.57 uvicorn app.main:app --port 8080
```

| Variable | Standard | Bedeutung |
|---|---|---|
| `ORBITDESK_NORAD_ID` | `59112` | Katalognummer des Satelliten (SONATE-2) |
| `ORBITDESK_SATELLITE_NAME` | `SONATE-2` | Anzeigename |
| `ORBITDESK_STATION_NAME` | `TU Berlin` | Name der Bodenstation |
| `ORBITDESK_STATION_LAT` / `_LON` / `_ALT` | `52.51` / `13.33` / `60` | Position der Bodenstation (Grad, Meter) |
| `ORBITDESK_TLE_ONLINE` | `true` | `false` = nie ins Internet (reiner Offline-Betrieb) |
| `ORBITDESK_TLE_REFRESH_HOURS` | `6` | Wie oft die TLE neu geladen wird |
| `ORBITDESK_TLE_WARN_AGE_DAYS` | `14` | Ab welchem Alter gewarnt wird |
| `ORBITDESK_RETENTION_HOURS` | `24` | Aufbewahrung der Telemetrie (Missionszeit) |
| `ORBITDESK_DATA_DIR` | `./data` | Ordner für Datenbank und TLE-Cache |
| `ORBITDESK_DATABASE_URL` | *(leer = SQLite)* | z. B. `postgresql+psycopg://user:pw@host/orbitdesk` |

**Produktname und Akzentfarbe** stehen zentral in
[`frontend/src/brand.ts`](frontend/src/brand.ts). Nach einer Änderung das
Frontend neu bauen (`npm run build` bzw. `docker compose up --build`).

**Offline-Demo mit echter Bahn:** OrbitDesk merkt sich die zuletzt geladene
TLE im Datenordner. Einmal mit Internet starten genügt – danach läuft die Demo
auch offline mit dieser TLE (Anzeige `CACHED`). Alternativ die aktuelle TLE von
<https://celestrak.org/NORAD/elements/gp.php?CATNR=59112&FORMAT=TLE> in
[`backend/app/orbit/fallback_tle.txt`](backend/app/orbit/fallback_tle.txt)
einfügen.

**Wechsel auf PostgreSQL/TimescaleDB:** `ORBITDESK_DATABASE_URL` setzen und
den passenden Treiber installieren (`pip install "psycopg[binary]"`). Der Code
greift ausschließlich über SQLAlchemy auf die Datenbank zu.

---

## Architektur und Ordnerstruktur

```
Browser (React)  ◄── WebSocket: Live-Telemetrie, Ereignisse, Status ──┐
      │                                                               │
      └── REST/JSON: Verlauf, Zeitraffer, TLE neu laden ──► FastAPI-Backend
                                                               │
          Missionsuhr ─► Simulator (Bahn via Skyfield, Sonne, Batterie,
          (Zeitraffer)    Thermik, Lage, Fehler) ─► SQLite ─► Verteiler
```

- **Eine Missionsuhr** für alles: Bahnposition, Tag/Nacht und Telemetrie
  laufen im Zeitraffer synchron.
- **Physik statt Zufallszahlen:** Ob der Satellit im Erdschatten ist, wird aus
  der echten Bahn (TLE + Skyfield/SGP4) und dem Sonnenstand berechnet. Daraus
  ergeben sich Solarleistung, Batterieladung und Temperaturen.
- **Ein Prozess, ein Container:** FastAPI liefert API, WebSocket und die
  gebaute Oberfläche aus.

```
space-satellite/
├── README.md
├── docker-compose.yml          Start mit einem Befehl
├── Dockerfile                  Stufe 1: Frontend bauen, Stufe 2: Python
├── backend/
│   ├── requirements.txt        Python-Abhängigkeiten
│   ├── app/
│   │   ├── main.py             FastAPI-App, WebSocket, Auslieferung der Oberfläche
│   │   ├── config.py           Einstellungen (Umgebungsvariablen)
│   │   ├── clock.py            Missionsuhr mit Zeitraffer
│   │   ├── mission.py          Missionskern: Hintergrundschleifen, Speichern, Verteilen
│   │   ├── parameters.py       Katalog der Messwerte (Einheit, Standard-Grenzwerte)
│   │   ├── limits.py           Grenzwertprüfung & Alarmlogik (mit Hysterese)
│   │   ├── commands.py         Befehlskatalog & Freigabeprozess
│   │   ├── users.py            Demo-Personen und Rollenrechte
│   │   ├── audit.py            Betriebsprotokoll (wer, wann, was)
│   │   ├── sources.py          Schnittstelle "Telemetrie-Quelle" (Simulator ↔ echte Bodenstation)
│   │   ├── db.py, models.py    Datenbank (SQLAlchemy) und Tabellen
│   │   ├── ws.py               WebSocket-Verteiler
│   │   ├── schemas.py          Formate der API-Anfragen
│   │   ├── api/                REST-Endpunkte (system, telemetry, alarms, passes, commands)
│   │   ├── orbit/tle.py        TLE laden (CelesTrak → Cache → Ersatz-TLE)
│   │   ├── orbit/passes.py     Überflugberechnung, Bodenstation, Himmelsbahn
│   │   └── simulator/
│   │       ├── cubesat.py      Zustandsmodell des CubeSats
│   │       ├── sun.py          Sonnenstand und Erdschatten
│   │       └── faults.py       Fehlerbilder
│   └── tests/                  pytest-Tests
└── frontend/
    ├── package.json, vite.config.ts, tsconfig.json, index.html
    └── src/
        ├── brand.ts            ★ Produktname + Akzentfarbe
        ├── App.tsx             Kopfzeile, Tabs, Seiten
        ├── hooks/useLiveData.ts  WebSocket-Verbindung mit Auto-Reconnect
        ├── components/         Header, Kacheln, Diagramme, Alarmanzeige, Personenauswahl …
        ├── pages/              Dashboard, Passes, Commands, Alarms, Limits, Log
        └── styles/theme.css    dunkles Kontrollraum-Design
```

---

## Tests

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Die Tests prüfen u. a.: gültige TLE und Prüfsummen, Sonnenabstand und
Schattengeometrie, realistischen Eklipse-Anteil (25–40 % des Orbits),
Fehlerbilder (Heizungsausfall kühlt die Batterie unter 0 °C), Hysterese und
Eskalation der Alarme, Rollenrechte (Engineer darf nichts ändern),
plausible Überflüge (Anzahl, Dauer, Elevation; höhere Mindestelevation = weniger
Überflüge), Bodenstation ändern, Vorspulen, der Befehlsablauf (Rechte,
Vier-Augen-Prinzip, Senden nur im Überflug, ungültige Befehle, Ablehnen mit
Begründung) und die API.

---

## Fachbegriffe

| Begriff | Erklärung |
|---|---|
| **Telemetrie** | Messwerte, die der Satellit zur Erde funkt (Spannungen, Temperaturen, Lage …) |
| **TLE** | *Two-Line Element Set* – Bahndaten eines Satelliten in zwei Textzeilen, gültig für einen Zeitpunkt (Epoche) |
| **NORAD-ID** | Weltweit eindeutige Katalognummer eines Objekts im Erdorbit |
| **CelesTrak** | Öffentliche Quelle für aktuelle TLEs |
| **SGP4 / Skyfield** | SGP4 ist das Standard-Rechenmodell für TLEs; Skyfield ist die Python-Bibliothek, die es nutzt |
| **LEO** | *Low Earth Orbit* – niedrige Erdumlaufbahn (hier ~520 km, ein Umlauf ~95 min) |
| **Eklipse** | Phase im Erdschatten: keine Solarleistung, der Satellit kühlt ab |
| **Sonnensynchrone Bahn** | Polnahe Bahn, die die Erde immer zur gleichen Ortszeit überfliegt |
| **EPS** | *Electrical Power System* – Energieversorgung (Solarzellen, Batterie) |
| **SoC** | *State of Charge* – Ladezustand der Batterie in % |
| **ADCS** | *Attitude Determination and Control System* – Lagebestimmung und -regelung |
| **Reaktionsrad** | Schwungrad, mit dem der Satellit seine Ausrichtung ändert |
| **OBC** | *On-Board Computer* – Bordcomputer |
| **FDIR** | *Fault Detection, Isolation and Recovery* – Bordsoftware, die Fehler selbst erkennt und den Satelliten schützt |
| **SAFE-Modus** | Sicherheitsmodus: Nutzlast aus, Satellit wartet auf Anweisungen vom Boden |
| **Latch-up** | Kurzschluss in einem Chip, ausgelöst durch ein energiereiches Teilchen aus der Weltraumstrahlung |
| **Überflug (Pass)** | Zeitspanne, in der der Satellit über dem Horizont der Bodenstation steht und Funkkontakt möglich ist |
| **AOS / LOS** | *Acquisition / Loss of Signal* – Beginn und Ende des Funkkontakts |
| **Elevation / Azimut** | Höhe über dem Horizont (0–90°) bzw. Himmelsrichtung (0° = Nord, 90° = Ost) |
| **Mindestelevation** | Untergrenze, ab der Kontakt zählt (Gebäude, Bäume und schwaches Signal knapp über dem Horizont) |
| **Sky Plot** | Himmelskarte eines Überflugs aus Sicht der Antenne |
| **Telekommando (Command)** | Befehl vom Boden an den Satelliten |
| **Uplink** | Funkstrecke vom Boden zum Satelliten (Gegenteil: Downlink für Telemetrie) |
| **ACK** | *Acknowledgement* – Bestätigung des Satelliten, dass er den Befehl erhalten und ausgeführt hat |
| **Vier-Augen-Prinzip** | Eine zweite Person prüft und gibt frei, bevor ein Befehl gesendet wird |
| **Grenzwert (Limit)** | Wert, ab dem ein Messwert als auffällig (Warnung) oder gefährlich (kritisch) gilt |
| **Hysterese** | Kleiner Sicherheitsabstand, damit ein Alarm bei rauschenden Werten nicht ständig an- und ausgeht |
| **Quittieren / Bestätigen** | Ein Mensch bestätigt, dass er den Alarm gesehen hat |
| **Audit-Log** | Unveränderliches Protokoll aller Bedienaktionen |
| **UTC** | Koordinierte Weltzeit – in der Raumfahrt die gemeinsame Zeitbasis |

---

## Grenzen des Prototyps

- Die Telemetrie ist simuliert; das Modell ist vereinfacht und nicht auf
  SONATE-2 abgestimmt.
- Die eingebaute Ersatz-TLE ist eine **Annäherung** an die Bahn von SONATE-2
  (sonnensynchron, ~520 km). Für realistische Bahn- und Überflugdaten wird die
  aktuelle TLE von CelesTrak verwendet, sobald Internet verfügbar ist.
- Kein Login: Die Person wird nur ausgewählt (Kopffeld `X-OrbitDesk-User`).
  Für das Produkt wird an genau einer Stelle (`backend/app/users.py`,
  `current_user`) echtes Login eingesetzt; alle Rechteprüfungen bleiben gleich.
- Datenbank-Tabellen werden beim Start automatisch angelegt (keine
  Migrationen). Für ein Produkt würde man Alembic einsetzen.
