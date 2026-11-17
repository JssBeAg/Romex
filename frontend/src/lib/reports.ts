import { type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

// A photo of the report; `url` is relative to /api/ and needs the session to be fetched
export type Evidence = { id: number; name: string; url: string };

export type Report = {
  id: number;
  title: string; // how the record is identified: kind, enrollment IDs, date, economic number
  date: string; // YYYY-MM-DD
  location: string;
  evidence: Evidence[];
  description: string;
  status: Option;
  unit: Option;
  reported_by: Option;
  has_diagnosis: boolean;
  status_history: StatusChange[];
  // Mechanics assigned to the report, current and past (only the manager receives them)
  mechanics?: MechanicAssignment[];
  // The manager can assign mechanics while the report is not repaired
  can_assign?: boolean;
  // True only for the operator who wrote it, while it is still pending
  can_modify: boolean;
};

// One line of the history of statuses of a report (oldest first)
export type StatusChange = {
  id: number;
  status: string;
  changed_at: string; // ISO date and time
  changed_by: string; // who caused it, or "Sistema"
};

export type MechanicAssignment = {
  id: number;
  mechanic: Option;
  start_date: string; // YYYY-MM-DD
  end_date: string | null; // no end date: assigned now
};

export type ReportInput = {
  unit_id: number | null;
  location: string;
  date: string;
  description: string;
  images: File[]; // new photos to attach
  remove_evidence_ids: number[]; // photos already attached to remove (when editing)
};

// `mechanics` only comes for the manager
export type ReportCatalogs = { units: Option[]; statuses: Option[]; mechanics?: Option[] };

export const listReports = (params: ListParams = {}) =>
  request<{ reports: Report[]; pagination: Pagination }>(`reportes-fallas/${toQuery(params)}`, "GET");

export const getReport = (id: number) =>
  request<{ report: Report }>(`reportes-fallas/${id}/`, "GET");

// The form goes as multipart: the fields plus the photos
function toFormData(input: ReportInput): FormData {
  const form = new FormData();
  form.append("unit_id", input.unit_id === null ? "" : String(input.unit_id));
  form.append("location", input.location);
  form.append("date", input.date);
  form.append("description", input.description);
  input.images.forEach((file) => form.append("images", file));
  input.remove_evidence_ids.forEach((id) => form.append("remove_evidence_ids", String(id)));
  return form;
}

export const createReport = (input: ReportInput) =>
  request<{ report: Report }>("reportes-fallas/", "POST", toFormData(input));

export const updateReport = (id: number, input: ReportInput) =>
  request<{ report: Report }>(`reportes-fallas/${id}/`, "PUT", toFormData(input));

// Limits (the server enforces them too)
export const MAX_IMAGES = 5;
export const MAX_IMAGE_MB = 5;
export const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

export const deleteReport = (id: number) =>
  request<{ ok: boolean }>(`reportes-fallas/${id}/`, "DELETE");

export const getReportCatalogs = () =>
  request<ReportCatalogs>("reportes-fallas/catalogos/", "GET");

// The manager assigns a mechanic to a report, and later ends the assignment.
export const assignMechanic = (reportId: number, mechanicId: number, startDate: string) =>
  request<{ report: Report }>(`reportes-fallas/${reportId}/mecanicos/`, "POST", {
    mechanic_id: mechanicId,
    start_date: startDate,
  });

export const endMechanicAssignment = (reportId: number, assignmentId: number, endDate: string) =>
  request<{ report: Report }>(`reportes-fallas/${reportId}/mecanicos/${assignmentId}/`, "PUT", {
    end_date: endDate,
  });
