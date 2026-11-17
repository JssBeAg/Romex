import { request } from "./http";
import type { DueRow } from "./preventive";
import type { Unit } from "./units";

export type KardexEventType = "plate" | "operator" | "mechanic" | "report" | "diagnosis" | "maintenance" | "checklist" | "change";

export type KardexEvent = {
  type: KardexEventType;
  date: string; // YYYY-MM-DD
  title: string;
  detail: string;
  link: string | null; // page of the record, when it has one
};

export type KardexSummary = {
  reports: number;
  pending_reports: number;
  diagnoses: number;
  maintenances: number;
  preventive_maintenances: number;
  corrective_maintenances: number;
  total_maintenance_cost: string;
  last_maintenance: { date: string; mileage: number } | null;
  checklists: number;
  last_checklist: { date: string; mileage: number } | null;
};

export type PartUsed = { id: number; label: string; pieces: number; times: number; last_date: string };

export type Kardex = {
  unit: Unit;
  summary: KardexSummary;
  preventive: DueRow[];
  parts_used: PartUsed[];
  events: KardexEvent[];
};

// The kardex is not stored: the server computes it from the other tables each time
export const getKardex = (unitId: number) => request<Kardex>(`kardex/${unitId}/`, "GET");

export const EVENT_LABELS: Record<KardexEventType, string> = {
  plate: "Placa",
  operator: "Operador",
  mechanic: "Mecánico",
  report: "Reporte",
  diagnosis: "Diagnóstico",
  maintenance: "Mantenimiento",
  checklist: "Checklist",
  change: "Cambio de datos",
};
