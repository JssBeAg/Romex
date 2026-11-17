import { request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type HistoryEvent = {
  date: string; // YYYY-MM-DD
  id: number;
  kind: string; // Entrada, Ajuste, Uso en mantenimiento
  change: number; // pieces: positive come in, negative go out
  detail: string;
  who: string;
  link: string | null; // the maintenance that used the pieces
  balance: number; // stock left after this event
};

export type SparePart = {
  id: number;
  name: string;
  description: string;
  unit_price: string | null; // reference price, decimal as text
  min_stock: number;
  is_active: boolean;
  photo_url: string | null; // API path of the photo; null when there is none
  stock: number; // pieces in stock now (worked out by the server)
  used: number; // pieces used in maintenances so far
  low_stock: boolean; // stock <= min_stock
  can_delete: boolean; // no maintenance has used it
  history?: HistoryEvent[]; // only when asking for one part
};

export type SparePartInput = {
  name: string;
  description: string;
  unit_price: string;
  min_stock: string;
  is_active: boolean;
  initial_stock: string; // only used when creating
};

export type MovementInput = {
  movement_type: "entrada" | "ajuste" | "";
  quantity: string;
  date: string;
  note: string;
};

export const listSpareParts = (params: ListParams = {}) =>
  request<{ spare_parts: SparePart[]; low_stock_count: number; pagination: Pagination }>(
    `refacciones/${toQuery(params)}`,
    "GET"
  );

export const getSparePart = (id: number) =>
  request<{ spare_part: SparePart }>(`refacciones/${id}/`, "GET");

export const createSparePart = (input: SparePartInput) =>
  request<{ spare_part: SparePart }>("refacciones/", "POST", input);

export const updateSparePart = (id: number, input: SparePartInput) =>
  request<{ spare_part: SparePart }>(`refacciones/${id}/`, "PUT", input);

export const deleteSparePart = (id: number) =>
  request<{ ok: boolean }>(`refacciones/${id}/`, "DELETE");

export const uploadPartPhoto = (id: number, file: File) => {
  const form = new FormData();
  form.append("photo", file);
  return request<{ spare_part: SparePart }>(`refacciones/${id}/foto/`, "POST", form);
};

export const deletePartPhoto = (id: number) =>
  request<{ spare_part: SparePart }>(`refacciones/${id}/foto/`, "DELETE");

export const addMovement = (id: number, input: MovementInput) =>
  request<{ spare_part: SparePart }>(`refacciones/${id}/movimientos/`, "POST", input);
