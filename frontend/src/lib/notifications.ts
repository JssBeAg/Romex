import { request } from "./http";
import { type ListParams, type Pagination, toQuery } from "./listing";

export type Notification = {
  id: number;
  kind: string;
  kind_label: string;
  message: string;
  link: string; // a page of the frontend, or empty
  is_read: boolean;
  created_at: string;
};

export type NotificationPage = {
  notifications: Notification[];
  pagination: Pagination;
  unread: number;
  kinds: { id: string; label: string }[];
};

// The menu listens to this event to refresh the number on the bell
export const NOTIFICATIONS_CHANGED = "romex:notifications-changed";

export const listNotifications = (params: ListParams = {}) =>
  request<NotificationPage>(`notificaciones/${toQuery(params)}`, "GET");

export const getUnreadCount = () => request<{ unread: number }>("notificaciones/resumen/", "GET");

// With ids: those notifications; without: all of the user's
export async function markRead(ids?: number[]) {
  const res = await request<{ updated: number }>("notificaciones/leer/", "POST", ids ? { ids } : {});
  if (typeof window !== "undefined") window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED));
  return res;
}

export async function clearRead() {
  const res = await request<{ deleted: number }>("notificaciones/limpiar/", "POST", {});
  if (typeof window !== "undefined") window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED));
  return res;
}
