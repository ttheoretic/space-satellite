// Gemeinsame Datentypen. Sie spiegeln die JSON-Antworten des Backends wider.

export interface Parameter {
  key: string;
  label: string;
  unit: string;
  group: "power" | "thermal" | "attitude";
  decimals: number;
  description: string;
  crit_low: number | null;
  warn_low: number | null;
  warn_high: number | null;
  crit_high: number | null;
}

/** Ein Telemetrie-Paket, wie es der (simulierte) Satellit sendet. */
export interface Frame {
  seq: number;
  t: string; // ISO-Zeitstempel (UTC, Missionszeit)
  mode: "NOMINAL" | "SAFE";
  eclipse: boolean;
  illumination: number; // 0..1
  heater_on: boolean;
  heater_mode: "AUTO" | "ON" | "OFF";
  faults: string[];
  position: { lat: number; lon: number; alt_km: number };
  values: Record<string, number>;
}

export interface TleStatus {
  name: string;
  norad_id: number;
  source: "live" | "cache" | "fallback";
  epoch: string;
  fetched_at: string | null;
  age_days: number;
  warn: boolean;
  warn_age_days: number;
  line1: string;
  line2: string;
  last_error: string | null;
}

export interface Status {
  satellite: { name: string; norad_id: number };
  station: { name: string; lat: number; lon: number; alt_m: number };
  clock: { mission_time: string; speed: number; speed_options: number[] };
  tle: TleStatus;
  simulator: { random_faults: boolean };
}

export interface SpacecraftEvent {
  t: string | null;
  level: "info" | "warning";
  text: string;
}

export type ConnectionState = "connecting" | "live" | "offline";
