import { type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type PlateEntry = {
  identifier: string;
  state: string;
  start_date: string; // YYYY-MM-DD
  end_date: string | null; // null = the plate the unit has now
};

// An operator having a unit: since when until when (null = has it now)
export type OperatorAssignment = {
  id: number;
  operator: Option;
  start_date: string; // YYYY-MM-DD
  end_date: string | null;
};

export type Unit = {
  id: number;
  economic_number: string;
  mileage: number;
  is_active: boolean;
  unit_model: Option;
  brand: Option;
  current_plate: PlateEntry | null;
  plate_history: PlateEntry[]; // newest first
  // The one operator who has the unit now (an open assignment), or null
  current_operator: OperatorAssignment | null;
  operators: OperatorAssignment[]; // the whole history, newest first
};

export type UnitInput = {
  economic_number: string;
  unit_model_id: number | null;
  mileage: string;
  is_active: boolean;
  // Required when creating. When editing: null keeps the current plate, an object replaces it.
  plate: { state: string; identifier: string; start_date: string } | null;
  // Change of operator, applied when saving. Both together = change of operator (one transaction).
  end_operator: { assignment_id: number; end_date: string } | null; // end the current assignment
  new_operator: { operator_id: number; start_date: string } | null; // open a new one
};

export type UnitCatalogs = {
  brands: Option[];
  models: (Option & { brand_id: number })[];
  // Active operators without a unit (the ones that can be assigned), plus the unit's current one
  operators: (Option & { current: boolean })[];
};

export type StatusFilter = "active" | "inactive" | "all";

export const listUnits = (params: ListParams = {}) =>
  request<{ units: Unit[]; pagination: Pagination }>(`unidades/${toQuery(params)}`, "GET");

export const getUnit = (id: number) => request<{ unit: Unit }>(`unidades/${id}/`, "GET");

export const createUnit = (input: UnitInput) => request<{ unit: Unit }>("unidades/", "POST", input);

export const updateUnit = (id: number, input: UnitInput) =>
  request<{ unit: Unit }>(`unidades/${id}/`, "PUT", input);

export const deleteUnit = (id: number) => request<{ ok: boolean }>(`unidades/${id}/`, "DELETE");

export const getUnitCatalogs = (unitId?: number) =>
  request<UnitCatalogs>(`unidades/catalogos/${unitId ? `?unidad=${unitId}` : ""}`, "GET");
