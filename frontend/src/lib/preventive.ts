import { type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type DueStatus = "vencido" | "proximo" | "sin_historial" | "al_corriente";

export type DueRow = {
  unit: Option; // the unit (economic number)
  plan: { id: number; name: string; every_km: number | null; every_days: number | null };
  status: DueStatus;
  status_label: string;
  message: string; // e.g. "Faltan 800 km. Faltan 12 días."
  current_mileage: number;
  last: { id: number; date: string; mileage: number } | null; // the last service of the plan
  next_km: number | null;
  remaining_km: number | null; // negative: already passed
  next_date: string | null;
  remaining_days: number | null;
};

export type DueSummary = { overdue: number; upcoming: number; no_history: number; ok: number };

export type Plan = {
  id: number;
  name: string;
  description: string;
  every_km: number | null;
  every_days: number | null;
  unit_model: Option | null; // null: applies to every unit
  is_active: boolean;
  services: number | null; // maintenances that fulfilled it
  can_delete: boolean;
};

export type PlanInput = {
  name: string;
  description: string;
  every_km: string;
  every_days: string;
  unit_model_id: number | null;
  is_active: boolean;
};

export const getDue = (status = "", search = "") => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search) params.set("q", search);
  const query = params.toString();
  return request<{ rows: DueRow[]; summary: DueSummary }>(`preventivo/vencimientos/${query ? `?${query}` : ""}`, "GET");
};

export const listPlans = (params: ListParams = {}) =>
  request<{ plans: Plan[]; pagination: Pagination }>(`preventivo/planes/${toQuery(params)}`, "GET");

export const getPlan = (id: number) => request<{ plan: Plan }>(`preventivo/planes/${id}/`, "GET");

export const createPlan = (input: PlanInput) => request<{ plan: Plan }>("preventivo/planes/", "POST", input);

export const updatePlan = (id: number, input: PlanInput) =>
  request<{ plan: Plan }>(`preventivo/planes/${id}/`, "PUT", input);

export const deletePlan = (id: number) => request<{ ok: boolean }>(`preventivo/planes/${id}/`, "DELETE");

export const getPlanCatalogs = () => request<{ models: Option[] }>("preventivo/catalogos/", "GET");
