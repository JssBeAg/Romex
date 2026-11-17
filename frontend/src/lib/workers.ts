import { type ApiResult, type FieldErrors, type Option, request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type { ApiResult, FieldErrors, Option };

export { MANAGER_ROLE } from "./roles";

export type WorkerAddress = {
  state: string;
  municipality: string;
  neighborhood: string;
  street: string;
  exterior_number: string;
  interior_number: string;
};

// Dialing code of a country, as the API sends it (label: "México (+52)")
export type PhoneCodeOption = { id: number; iso: string; code: string; label: string };

// Another way to reach the same worker: a second phone or email
export type WorkerContact = {
  id: number;
  kind: "telefono" | "correo";
  phone_code_id: number | null; // only phones have a code
  phone_code: PhoneCodeOption | null;
  value: string;
  display: string; // "+52 8441234567" or the email
  label: string; // "Número 2"
  contact_name: string; // optional: whose number/email it is
};

export type ContactInput = {
  id: number | null; // null = new
  kind: "telefono" | "correo";
  phone_code_id: number | null;
  value: string;
  label: string;
  contact_name: string;
};

export type Worker = {
  id: number;
  enrollment_id: string;
  first_name: string;
  paternal_surname: string;
  maternal_surname: string;
  email: string;
  phone_code: PhoneCodeOption | null;
  phone_number: string; // national number, digits only
  phone_display: string; // "+52 8441234567"
  contacts: WorkerContact[];
  is_active: boolean;
  must_change_password: boolean;
  locked: boolean; // blocked for too many failed logins
  photo_url: string | null; // API path of the profile photo; null when there is none
  sex: Option;
  role: Option | null;
  // Units this operator has now (read only: they are assigned from the unit)
  assigned_units: { id: number; economic_number: string; start_date: string }[];
  // Reports this mechanic has now (read only: they are assigned from the report)
  assigned_reports: { id: number; economic_number: string; date: string; location: string; start_date: string }[];
  address: WorkerAddress;
};

// What the form sends. The password is optional when editing (empty = keep the current one).
export type WorkerInput = {
  enrollment_id: string;
  first_name: string;
  paternal_surname: string;
  maternal_surname: string;
  email: string;
  phone_code_id: number | null;
  phone_number: string;
  contacts: ContactInput[];
  sex_id: number | null;
  role_id: number | null;
  is_active: boolean;
  password: string;
  address: {
    state: string;
    municipality: string;
    neighborhood: string;
    street: string;
    exterior_number: string;
    interior_number: string;
  };
};

export type Catalogs = {
  sexes: Option[];
  roles: Option[];
  phone_codes: PhoneCodeOption[];
  max_contacts: number;
};

export const listWorkers = (params: ListParams = {}) =>
  request<{ workers: Worker[]; pagination: Pagination }>(`trabajadores/${toQuery(params)}`, "GET");

export const getWorker = (id: number) => request<{ worker: Worker }>(`trabajadores/${id}/`, "GET");

export const createWorker = (input: WorkerInput) =>
  request<{ worker: Worker }>("trabajadores/", "POST", input);

export const updateWorker = (id: number, input: WorkerInput) =>
  request<{ worker: Worker }>(`trabajadores/${id}/`, "PUT", input);

export const deleteWorker = (id: number) => request<{ ok: boolean }>(`trabajadores/${id}/`, "DELETE");

export const getCatalogs = () => request<Catalogs>("trabajadores/catalogos/", "GET");

// Profile photo (optional). The limits are checked here too, so the person finds out before sending it.
export const PHOTO_MAX_MB = 5;
export const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

/** A message when the file cannot be used as a photo, or "" when it looks fine. */
export function photoProblem(file: File): string {
  if (!PHOTO_TYPES.includes(file.type)) return "La fotografía debe ser JPG, PNG o WebP.";
  if (file.size > PHOTO_MAX_MB * 1024 * 1024) return `La fotografía pesa más de ${PHOTO_MAX_MB} MB.`;
  return "";
}

export const uploadWorkerPhoto = (id: number, file: File) => {
  const form = new FormData();
  form.append("photo", file);
  return request<{ worker: Worker }>(`trabajadores/${id}/foto/`, "POST", form);
};

export const deleteWorkerPhoto = (id: number) =>
  request<{ worker: Worker }>(`trabajadores/${id}/foto/`, "DELETE");
