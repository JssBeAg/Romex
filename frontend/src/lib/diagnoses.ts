import { type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type Diagnosis = {
  id: number;
  title: string; // how the record is identified: kind, enrollment IDs, date, economic number
  date: string; // YYYY-MM-DD
  detailed_cause: string;
  requires_repair: boolean;
  unit_operable: boolean;
  severity: Option;
  fault_report: Option & { title: string; description: string };
  unit: Option;
  diagnosed_by: Option;
  maintenances_count: number;
  // True only for the mechanic who wrote it
  can_modify: boolean;
};

export type DiagnosisInput = {
  fault_report_id: number | null; // only used when creating
  date: string;
  detailed_cause: string;
  requires_repair: boolean | null;
  unit_operable: boolean | null;
  severity_id: number | null;
};

// Each report carries its description, so the form can show it once the report is chosen
export type DiagnosisCatalogs = { severities: Option[]; reports: (Option & { description: string })[] };

export const listDiagnoses = (params: ListParams = {}) =>
  request<{ diagnoses: Diagnosis[]; pagination: Pagination }>(`diagnosticos/${toQuery(params)}`, "GET");

export const getDiagnosis = (id: number) =>
  request<{ diagnosis: Diagnosis }>(`diagnosticos/${id}/`, "GET");

export const createDiagnosis = (input: DiagnosisInput) =>
  request<{ diagnosis: Diagnosis }>("diagnosticos/", "POST", input);

export const updateDiagnosis = (id: number, input: DiagnosisInput) =>
  request<{ diagnosis: Diagnosis }>(`diagnosticos/${id}/`, "PUT", input);

export const deleteDiagnosis = (id: number) =>
  request<{ ok: boolean }>(`diagnosticos/${id}/`, "DELETE");

export const getDiagnosisCatalogs = () =>
  request<DiagnosisCatalogs>("diagnosticos/catalogos/", "GET");
