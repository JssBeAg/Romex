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
  operators: OperatorAssignment[]; // newest first
};

export type UnitInput = {
  economic_number: string;
  unit_model_id: number | null;
  mileage: string;
  is_active: boolean;
  // Required when creating. When editing: null keeps the current plate, an object replaces it.
  plate: { state: string; identifier: string; start_date: string } | null;
  // Operators to assign, and assignments to end (applied when saving)
  add_operators: { operator_id: number; start_date: string }[];
  end_operators: { assignment_id: number; end_date: string }[];
};

export type UnitCatalogs = {
  brands: Option[];
  models: (Option & { brand_id: number })[];
  operators: Option[]; // active operators, the ones that can be assigned
};

export type StatusFilter = "active" | "inactive" | "all";

export const listUnits = (params: ListParams = {}) =>
  request<{ units: Unit[]; pagination: Pagination }>(`unidades/${toQuery(params)}`, "GET");

export const getUnit = (id: number) => request<{ unit: Unit }>(`unidades/${id}/`, "GET");

export const createUnit = (input: UnitInput) => request<{ unit: Unit }>("unidades/", "POST", input);

export const updateUnit = (id: number, input: UnitInput) =>
  request<{ unit: Unit }>(`unidades/${id}/`, "PUT", input);

export const deleteUnit = (id: number) => request<{ ok: boolean }>(`unidades/${id}/`, "DELETE");

export const getUnitCatalogs = () => request<UnitCatalogs>("unidades/catalogos/", "GET");
