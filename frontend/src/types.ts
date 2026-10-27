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
