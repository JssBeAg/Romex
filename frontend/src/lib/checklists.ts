import { type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type Checklist = {
  id: number;
  title: string; // how the record is identified: kind, folio, date, economic number
  folio: string;
  date: string; // YYYY-MM-DD
  unit: Option;
  completed_by: Option;
  recorded_mileage: number;
  tire_pressure: string; // PSI
  tire_tread_depth: string; // mm
  lights_ok: boolean;
  fluids_ok: boolean;
  no_cracks: boolean;
  trip_description: string;
  // True only for the operator who wrote it
  can_modify: boolean;
};

// Each check is answered explicitly, so it starts as null (unanswered)
export type ChecklistInput = {
  unit_id: number | null;
  date: string;
  recorded_mileage: string;
  tire_pressure: string;
  tire_tread_depth: string;
  lights_ok: boolean | null;
  fluids_ok: boolean | null;
  no_cracks: boolean | null;
  trip_description: string;
};

export const listChecklists = (params: ListParams = {}) =>
  request<{ checklists: Checklist[]; pagination: Pagination }>(`checklists/${toQuery(params)}`, "GET");

export const getChecklist = (id: number) =>
  request<{ checklist: Checklist }>(`checklists/${id}/`, "GET");

export const createChecklist = (input: ChecklistInput) =>
  request<{ checklist: Checklist }>("checklists/", "POST", input);

export const updateChecklist = (id: number, input: ChecklistInput) =>
  request<{ checklist: Checklist }>(`checklists/${id}/`, "PUT", input);

export const deleteChecklist = (id: number) =>
  request<{ ok: boolean }>(`checklists/${id}/`, "DELETE");

export const getChecklistCatalogs = () =>
  // `units` are the ones fit to operate; `not_operable` are left out because a diagnosis says they cannot operate yet
  request<{ units: Option[]; not_operable: Option[] }>("checklists/catalogos/", "GET");

export const yesNo = (value: boolean) => (value ? "Sí" : "No");
