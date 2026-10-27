# OrbitDesk – Leitstand für kleine Satellitenmissionen (Prototyp)

OrbitDesk ist ein schlanker Leitstand im Browser für CubeSat-Teams und junge
New-Space-Startups. Dieser Prototyp dient als Demo für Kundengespräche.

> **Wichtig:** Alle Telemetrie in OrbitDesk ist **simuliert**. Die Bahn stammt
> aus echten TLE-Bahndaten von SONATE-2, Messwerte wie Batteriespannung oder
> Temperaturen erzeugt aber ein Simulator. Die Kopfzeile zeigt deshalb dauerhaft
> **„SIMULATED TELEMETRY“**.

**Stand: Schritt 1 von 4** – Simulator und Live-Dashboard.
Als Nächstes folgen Grenzwerte & Alarme, Überflugplanung und die Befehlsliste.

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

**Tab-Leiste** – rechts der Verbindungsstatus zum Server (`LIVE` /
`RECONNECTING`). Bricht die Verbindung ab, verbindet sich die Seite selbst neu.

**Dashboard**
- **Statusleiste:** Betriebsmodus (NOMINAL/SAFE), Sonne oder Erdschatten,
  Batterieheizung, Position über der Erde und Bahnhöhe
- **Power / Thermal / Attitude:** aktuelle Messwerte je Subsystem. Mit der Maus
  über einer Kachel erscheint eine Erklärung
- **Trends:** Verlaufsdiagramme für 30 min, 3 h oder 12 h. Grau hinterlegte
  Bereiche = Eklipse. So sieht man Ursache und Wirkung: Eintritt in den Schatten
  → Solarleistung fällt auf 0 → Ladezustand sinkt → Panels kühlen ab
- **Onboard Events:** Ereignisse an Bord (Eklipse, Moduswechsel, Fehler)
- **Simulation → Reset demo:** setzt Verlauf und Missionszeit zurück

Beim allerersten Start werden die letzten 3 Stunden „vorsimuliert“, damit die
Diagramme sofort Kurven zeigen.

---

## Demo-Drehbuch

Ein Vorschlag für ein Kundengespräch (wird mit jedem Bauschritt erweitert):

1. Dashboard zeigen, auf **SIMULATED TELEMETRY** und die **TLE-Anzeige**
   hinweisen: „Die Bahn ist die echte von SONATE-2, aktuell von CelesTrak.“
2. Diagramm **State of Charge** erklären: Sägezahn = Laden in der Sonne,
   Entladen im Schatten.
3. Auf **60×** schalten, Fenster **30 min**: Eintritt in die Eklipse live
   verfolgen – Solarleistung fällt, Panel-Temperatur sinkt, die Heizung
   schaltet sich ein.
4. Wieder auf **1×** stellen.

*(Ab Schritt 2: Fehler auslösen → Alarm → Bestätigen.)*

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
│   │   ├── db.py, models.py    Datenbank (SQLAlchemy) und Tabellen
│   │   ├── ws.py               WebSocket-Verteiler
│   │   ├── schemas.py          Formate der API-Anfragen
│   │   ├── api/                REST-Endpunkte (system, telemetry)
│   │   ├── orbit/tle.py        TLE laden (CelesTrak → Cache → Ersatz-TLE)
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
        ├── components/         Header, Kacheln, Diagramme, Statusleiste …
        ├── pages/Dashboard.tsx
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
Fehlerbilder (Heizungsausfall kühlt die Batterie unter 0 °C) und die API.

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
| **UTC** | Koordinierte Weltzeit – in der Raumfahrt die gemeinsame Zeitbasis |

---

## Grenzen des Prototyps

- Die Telemetrie ist simuliert; das Modell ist vereinfacht und nicht auf
  SONATE-2 abgestimmt.
- Die eingebaute Ersatz-TLE ist eine **Annäherung** an die Bahn von SONATE-2
  (sonnensynchron, ~520 km). Für realistische Bahn- und Überflugdaten wird die
  aktuelle TLE von CelesTrak verwendet, sobald Internet verfügbar ist.
- Kein Login; Personen und Rollen werden ab Schritt 2 nur für die Demo
  ausgewählt.
- Datenbank-Tabellen werden beim Start automatisch angelegt (keine
  Migrationen). Für ein Produkt würde man Alembic einsetzen.
