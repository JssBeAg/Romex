import { type Option, request } from "./http";

export type AuditChange = { field: string; old: string | number | boolean | null; new: string | number | boolean | null };

export type AuditEntry = {
  id: number;
  timestamp: string; // ISO date and time
  user_id: number | null;
  enrollment_id: string;
  user_name: string;
  role: string;
  action: string; // crear, modificar, eliminar, inicio_sesion, cierre_sesion, inicio_sesion_fallido
  action_label: string;
  table: string;
  table_label: string;
  record_id: number | null;
  record: string;
  changes: AuditChange[];
  ip_address: string | null;
};

export type AuditPage = { entries: AuditEntry[]; total: number; page: number; pages: number };

export type AuditCatalogs = { actions: Option[]; tables: Option[]; users: Option[] };

export type AuditFilters = {
  q: string;
  user_id: string;
  action: string;
  table: string;
  date_from: string;
  date_to: string;
};

export const EMPTY_FILTERS: AuditFilters = { q: "", user_id: "", action: "", table: "", date_from: "", date_to: "" };

// The trail is read only: there is no way to create, change or delete a line
export const listAudit = (filters: AuditFilters, page: number) => {
  const params = new URLSearchParams({ page: String(page) });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  return request<AuditPage>(`bitacora/?${params.toString()}`, "GET");
};

export const getAuditCatalogs = () => request<AuditCatalogs>("bitacora/catalogos/", "GET");
