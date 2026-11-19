import { type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";
import type { DueRow } from "./preventive";
import type { Unit } from "./units";

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

// The header of the kardex: the unit, its summary and its preventive plans
export type KardexHeader = {
  unit: Unit;
  summary: KardexSummary;
  preventive: DueRow[];
};

type RecordLink = { id: number; label: string };

export type KardexMaintenance = {
  id: number;
  folio: string;
  date: string;
  service_type: string; // "Preventivo" | "Correctivo"
  plan: string | null;
  mileage: number;
  cost: string;
  people: string[]; // who did it
  parts: { label: string; quantity: number }[];
  repair_completed: boolean | null; // null: preventive (no repair to finish)
  report: RecordLink | null;
  diagnosis: RecordLink | null;
  failure: string | null; // description of the report
  cause: string | null; // cause of the diagnosis
  observations: string;
};

export type KardexFault = {
  id: number;
  folio: string;
  date: string;
  reported_by: string;
  location: string;
  description: string;
  status: string;
  mechanics: string[]; // assigned now
  diagnosis: {
    id: number;
    folio: string;
    date: string;
    cause: string;
    severity: string;
    requires_repair: boolean;
    unit_operable: boolean;
  } | null;
};

export type KardexChecklist = {
  id: number;
  folio: string;
  date: string;
  operator: string;
  mileage: number;
  tire_pressure: string;
  tire_tread_depth: string;
  ok: boolean;
  failed_items: string[];
  trip_description: string;
};

export type KardexPart = { id: number; label: string; pieces: number; times: number; last_date: string };

export type KardexPerson = {
  id: string;
  role: string; // "Operador" | "Mecánico"
  person: string;
  start_date: string;
  end_date: string | null; // null: now
  report: RecordLink | null; // the report a mechanic was assigned to
};

export type KardexChange = {
  id: string;
  moment: string; // "YYYY-MM-DD HH:MM", Mexico City
  date: string;
  field: string;
  old: string;
  new: string;
  user: string;
};

export type KardexEventType = "plate" | "operator" | "mechanic" | "report" | "diagnosis" | "maintenance" | "checklist" | "change";

export type KardexEvent = {
  type: KardexEventType;
  type_label: string;
  date: string;
  title: string;
  detail: string;
  link: string | null; // page of the record, when it has one
};

// An option of a filter (the event types of the timeline have text ids)
export type FilterOption = { id: number | string; label: string };

// The answer of a section: its rows under `key`, the pagination and the options of its filters
export type SectionPage = {
  pagination: Pagination;
  statuses?: Option[];
  users?: Option[];
  types?: FilterOption[];
} & Record<string, unknown>;

// The kardex is not stored: the server computes it from the other tables each time
export const getKardex = (unitId: number) => request<KardexHeader>(`kardex/${unitId}/`, "GET");

// Path of a section, relative to /api/ (also what its PDF is asked for with)
export const sectionPath = (unitId: number, section: string) => `kardex/${unitId}/${section}/`;

export const listKardexSection = (unitId: number, section: string, params: ListParams) =>
  request<SectionPage>(`${sectionPath(unitId, section)}${toQuery(params)}`, "GET");
