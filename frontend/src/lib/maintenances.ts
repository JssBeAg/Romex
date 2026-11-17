import { type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type Maintenance = {
  id: number;
  title: string; // how the record is identified: kind, enrollment IDs, date, economic number
  date: string; // YYYY-MM-DD
  service_type: Option;
  service_mileage: number;
  total_cost: string; // decimal as text, e.g. "4850.50"
  observations: string;
  repair_completed: boolean; // corrective only: the repair is finished (the report becomes "Reparado")
  unit: Option;
  diagnosis: (Option & { detailed_cause: string }) | null; // null for preventive maintenance
  plan: Option | null; // the preventive plan it fulfils, if any
  operators: Option[];
  spare_parts: { id: number; label: string; quantity: number }[];
  // True only for a mechanic who took part in it
  can_modify: boolean;
};

export type MaintenanceInput = {
  // Only used when creating: the type, and the diagnosis (corrective) or the unit (preventive)
  service_type_id: number | null;
  diagnosis_id: number | null;
  unit_id: number | null;
  service_mileage: string;
  total_cost: string;
  date: string;
  observations: string;
  repair_completed: boolean; // only allowed for corrective maintenance
  plan_id: number | null; // preventive only: the plan it fulfils
  operator_ids: number[];
  // Parts used and how many pieces of each (the quantity goes as typed; the server checks it)
  spare_parts: { id: number; quantity: string }[];
};

export type MaintenanceCatalogs = {
  current_user_id: number;
  service_types: Option[];
  diagnoses: (Option & { detailed_cause: string })[];
  units: { id: number; label: string; unit_model_id: number }[];
  // Active preventive plans; a plan without model applies to every unit
  plans: { id: number; label: string; unit_model_id: number | null }[];
  operators: Option[];
  // `stock`: pieces in stock now
  spare_parts: { id: number; label: string; stock: number }[];
};

export const listMaintenances = (params: ListParams = {}) =>
  request<{ maintenances: Maintenance[]; pagination: Pagination }>(`mantenimientos/${toQuery(params)}`, "GET");

export const getMaintenance = (id: number) =>
  request<{ maintenance: Maintenance }>(`mantenimientos/${id}/`, "GET");

export const createMaintenance = (input: MaintenanceInput) =>
  request<{ maintenance: Maintenance }>("mantenimientos/", "POST", input);

export const updateMaintenance = (id: number, input: MaintenanceInput) =>
  request<{ maintenance: Maintenance }>(`mantenimientos/${id}/`, "PUT", input);

export const deleteMaintenance = (id: number) =>
  request<{ ok: boolean }>(`mantenimientos/${id}/`, "DELETE");

export const getMaintenanceCatalogs = () =>
  request<MaintenanceCatalogs>("mantenimientos/catalogos/", "GET");
