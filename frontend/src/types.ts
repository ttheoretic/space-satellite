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
  /** Nur verletzte Messwerte: Messwert → Stufe */
  limits?: Record<string, Severity>;
  /** Sichtbarkeit von der Bodenstation (fehlt im Vorlauf) */
  contact?: Contact;
}

export interface Contact {
  elevation: number;
  azimuth: number;
  range_km: number;
  in_contact: boolean;
}

export interface Station {
  name: string;
  lat: number;
  lon: number;
  alt_m: number;
  min_elevation: number;
}

/** Ein Überflug über die Bodenstation */
export interface Pass {
  id: string;
  aos: string; // Acquisition of Signal
  tca: string; // höchster Punkt
  los: string; // Loss of Signal
  duration_s: number;
  max_elevation: number;
  aos_azimuth: number;
  tca_azimuth: number;
  los_azimuth: number;
}

export interface PassesResponse {
  station: Station;
  generated_at: string;
  hours: number;
  tle_source: string;
  passes: Pass[];
}

export interface PassTrack extends Pass {
  track: { t: string; elevation: number; azimuth: number }[];
}

export type Severity = "warning" | "critical";

export interface Alarm {
  id: number;
  param_key: string;
  param_label: string;
  unit: string;
  decimals: number;
  severity: Severity; // höchste erreichte Stufe
  current: Severity | "ok"; // aktuelle Stufe
  active: boolean;
  acknowledged: boolean;
  limit_text: string;
  value_at_raise: number;
  last_value: number;
  raised_at: string;
  cleared_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
}

export interface LimitValues {
  crit_low: number | null;
  warn_low: number | null;
  warn_high: number | null;
  crit_high: number | null;
  enabled: boolean;
}

export interface LimitRow extends LimitValues {
  param_key: string;
  default: LimitValues;
  updated_by: string | null;
  updated_at: string | null;
}

export interface User {
  id: string;
  name: string;
  role: "operator" | "flight_director" | "engineer";
  role_label: string;
  permissions: string[];
}

export interface FaultType {
  key: string;
  label: string;
  description: string;
  recovery: string;
}

export interface AuditEntry {
  id: number;
  mission_time: string;
  real_time: string;
  user: string;
  action: string;
  details: Record<string, unknown>;
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
  station: Station;
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

export interface CommandDef {
  code: string;
  label: string;
  description: string;
  args: { name: string; options: string[] }[];
}

export type CommandStatus = "awaiting_approval" | "approved" | "rejected" | "sent" | "cancelled";

/** Ein Befehl in der Befehlsliste */
export interface Command {
  id: number;
  code: string;
  args: Record<string, string>;
  text: string; // z. B. "HEATER_MODE ON"
  comment: string;
  status: CommandStatus;
  pass_id: string | null;
  pass_aos: string | null;
  pass_los: string | null;
  pass_state: "upcoming" | "in_progress" | "over" | null;
  created_by: string;
  created_at: string;
  decided_by: string | null;
  decided_at: string | null;
  reject_reason: string | null;
  sent_by: string | null;
  sent_at: string | null;
  result: string | null;
}
