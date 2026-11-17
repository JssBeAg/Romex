import { API_URL, getCsrfToken } from "./api";

export type Option = { id: number; label: string };

// Field errors by field name, as returned by the API
export type FieldErrors = Record<string, string[]>;

export type ApiResult<T> = {
  ok: boolean;
  status: number;
  data?: T;
  errors?: FieldErrors;
  error?: string;
};

// Calls the API with the session cookie and, for changes, the CSRF token.
// The body is sent as JSON, or as a form (for files) when it is a FormData.
export async function request<T>(
  path: string,
  method: "GET" | "POST" | "PUT" | "DELETE",
  body?: unknown
): Promise<ApiResult<T>> {
  try {
    const headers: Record<string, string> = {};
    const isForm = body instanceof FormData;
    // With a FormData the browser sets the Content-Type itself (it includes the boundary)
    if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
    if (method !== "GET") headers["X-CSRFToken"] = await getCsrfToken();

    const res = await fetch(`${API_URL}/api/${path}`, {
      method,
      credentials: "include",
      headers,
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });
    const json = await res.json().catch(() => ({}));
    return {
      ok: res.ok,
      status: res.status,
      data: res.ok ? (json as T) : undefined,
      errors: json.errors,
      error: json.error,
    };
  } catch {
    return { ok: false, status: 0, error: "No se pudo conectar con el servidor" };
  }
}

// Asks the server to check what a form would send, without saving anything (?validar=1).
// `id` is the record being edited, or null for a new one. The problems come in `errors`.
export function validateOnServer(resource: string, id: number | null, body: unknown) {
  const path = id === null ? `${resource}/?validar=1` : `${resource}/${id}/?validar=1`;
  return request<{ errors: FieldErrors }>(path, id === null ? "POST" : "PUT", body);
}

// Downloads a protected file (an image) with the session cookie and returns it as a blob
export async function fetchBlob(path: string): Promise<Blob | null> {
  try {
    const res = await fetch(`${API_URL}/api/${path}`, { credentials: "include" });
    return res.ok ? await res.blob() : null;
  } catch {
    return null;
  }
}
