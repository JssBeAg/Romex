"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL } from "./api";
import type { ApiResult } from "./http";

// How the API pages a list: see backend/common/listing.py
export type Pagination = { page: number; pages: number; page_size: number; total: number };

export type ListParams = Record<string, string | number | boolean | undefined | null>;

// ?a=1&b=2 from the parameters that have a value
export function toQuery(params: ListParams): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "" || value === false) continue;
    query.set(key, value === true ? "1" : String(value));
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}

// Opens the PDF the API makes for `path` (a list with its filters, or one record) in a new tab,
// where the browser shows it and offers to print or save it.
// Returns an error message, or null when it was opened (or saved, if the tab could not be opened).
export async function openPdf(path: string, params: ListParams = {}): Promise<string | null> {
  // The tab is opened inside the click itself: a window opened after the request
  // finishes is taken for a pop-up and blocked by the browser.
  const tab = window.open("", "_blank");
  if (tab) {
    tab.document.title = "Generando PDF…";
    tab.document.body.textContent = "Generando PDF…";
  }
  try {
    // A PDF has no pages: the whole filtered list
    const { page: _page, page_size: _size, ...rest } = params;
    const res = await fetch(`${API_URL}/api/${path}${toQuery({ ...rest, format: "pdf" })}`, {
      credentials: "include",
    });
    if (!res.ok) {
      tab?.close();
      const body = await res.json().catch(() => ({}));
      return body.error ?? "No se pudo generar el PDF.";
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    if (tab && !tab.closed) {
      tab.location.href = url;
    } else {
      // Pop-ups blocked (or the tab was closed meanwhile): save the file instead
      const disposition = res.headers.get("Content-Disposition") ?? "";
      const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "romex.pdf";
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
    }
    // Kept for a while: the viewer in the tab may ask for the file again (save, print)
    setTimeout(() => URL.revokeObjectURL(url), 10 * 60 * 1000);
    return null;
  } catch {
    tab?.close();
    return "No se pudo conectar con el servidor";
  }
}

type Page<T, R> = { items: T[]; pagination: Pagination; data: R | null };

type Options<T, R> = {
  // Calls the API with the parameters; `rows` says where the rows are in the answer
  fetch: (params: ListParams) => Promise<ApiResult<R>>;
  rows: (data: R) => T[];
  initial?: ListParams;
  enabled?: boolean;
};

const EMPTY: Pagination = { page: 1, pages: 1, page_size: 20, total: 0 };

/**
 * State of a list page: the rows of the current page, the pagination and the parameters
 * (search, filters, order, page). Changing a filter or the order goes back to page 1.
 */
export function useList<T, R extends { pagination: Pagination }>({
  fetch: fetchPage,
  rows,
  initial = {},
  enabled = true,
}: Options<T, R>) {
  const [params, setParams] = useState<ListParams>({ page: 1, ...initial });
  const [page, setPage] = useState<Page<T, R>>({ items: [], pagination: EMPTY, data: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const turn = useRef(0);
  const latest = useRef({ fetchPage, rows });
  useEffect(() => {
    latest.current = { fetchPage, rows };
  });

  const key = JSON.stringify(params);
  const load = useCallback(async () => {
    const mine = ++turn.current;
    setLoading(true);
    const res = await latest.current.fetchPage(JSON.parse(key));
    if (mine !== turn.current) return; // a newer request took over
    setLoading(false);
    if (res.ok && res.data) {
      setPage({ items: latest.current.rows(res.data), pagination: res.data.pagination, data: res.data });
      setError("");
    } else {
      setError(res.error ?? "No se pudo cargar la lista");
    }
  }, [key]);

  useEffect(() => {
    if (enabled) load();
  }, [enabled, load]);

  // Changes some parameters; the page goes back to 1 unless the page itself is what changes
  const update = useCallback((changes: ListParams) => {
    setParams((previous) => ({ ...previous, page: "page" in changes ? changes.page : 1, ...changes }));
  }, []);

  // Click on a column: ascending, then descending, then ascending again
  const sortBy = useCallback((column: string) => {
    setParams((previous) => {
      const current = String(previous.order ?? "");
      const next = current === column ? `-${column}` : column;
      return { ...previous, order: next, page: 1 };
    });
  }, []);

  return { params, page, loading, error, update, sortBy, reload: load, setError };
}
