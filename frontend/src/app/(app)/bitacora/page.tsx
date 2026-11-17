"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import {
  type AuditCatalogs,
  type AuditChange,
  type AuditEntry,
  type AuditFilters,
  type AuditPage,
  EMPTY_FILTERS,
  getAuditCatalogs,
  listAudit,
} from "@/lib/audit";
import { MANAGER_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

// "2026-10-19 21:30:05", in the time zone of the person reading
function formatTime(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function formatValue(value: AuditChange["old"]): string {
  if (value === null || value === "") return "—";
  if (value === true) return "Sí";
  if (value === false) return "No";
  return String(value);
}

function Changes({ entry }: { entry: AuditEntry }) {
  if (entry.changes.length === 0) {
    return entry.ip_address ? <span className="hint">IP {entry.ip_address}</span> : <span>—</span>;
  }
  const created = entry.action === "crear";
  const deleted = entry.action === "eliminar";
  return (
    <details>
      <summary>
        {entry.changes.length} {entry.changes.length === 1 ? "campo" : "campos"}
      </summary>
      <ul className="audit-changes">
        {entry.changes.map((change) => (
          <li key={change.field}>
            <strong>{change.field}:</strong>{" "}
            {created ? (
              formatValue(change.new)
            ) : deleted ? (
              formatValue(change.old)
            ) : (
              <>
                <span className="audit-old">{formatValue(change.old)}</span> →{" "}
                <span className="audit-new">{formatValue(change.new)}</span>
              </>
            )}
          </li>
        ))}
      </ul>
      {entry.ip_address && <span className="hint">IP {entry.ip_address}</span>}
    </details>
  );
}

export default function AuditPageView() {
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [catalogs, setCatalogs] = useState<AuditCatalogs | null>(null);
  const [filters, setFilters] = useState<AuditFilters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<AuditFilters>(EMPTY_FILTERS); // what the list shows now
  const [data, setData] = useState<AuditPage | null>(null);
  const [loadError, setLoadError] = useState("");

  const load = useCallback(async (current: AuditFilters, page: number) => {
    const res = await listAudit(current, page);
    if (res.ok && res.data) {
      setData(res.data);
      setLoadError("");
    } else {
      setLoadError(res.error ?? "No se pudo cargar la bitácora");
    }
  }, []);

  useEffect(() => {
    if (!allowed) return;
    load(EMPTY_FILTERS, 1);
    getAuditCatalogs().then((res) => {
      if (res.ok && res.data) setCatalogs(res.data);
    });
  }, [allowed, load]);

  function set<K extends keyof AuditFilters>(key: K, value: string) {
    setFilters((previous) => ({ ...previous, [key]: value }));
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    setApplied(filters);
    load(filters, 1);
  }

  function handleClear() {
    setFilters(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    load(EMPTY_FILTERS, 1);
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Bitácora</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  const entries = data?.entries ?? [];

  return (
    <main>
      <h1>Bitácora</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>
      <p className="hint">
        Registro de quién hizo qué y cuándo. Se llena solo y no se puede modificar ni borrar. No incluye los accesos ni
        la actividad de las cuentas de administración.
      </p>

      <form onSubmit={handleSearch} className="audit-filters">
        <p>
          <label htmlFor="q">Buscar (matrícula, nombre o registro)</label>
          <br />
          <input id="q" value={filters.q} onChange={(e) => set("q", e.target.value)} />
        </p>
        <p>
          <label htmlFor="user_id">Usuario</label>
          <br />
          <select id="user_id" value={filters.user_id} onChange={(e) => set("user_id", e.target.value)}>
            <option value="">Todos</option>
            {catalogs?.users.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="action">Acción</label>
          <br />
          <select id="action" value={filters.action} onChange={(e) => set("action", e.target.value)}>
            <option value="">Todas</option>
            {catalogs?.actions.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="table">Tipo de registro</label>
          <br />
          <select id="table" value={filters.table} onChange={(e) => set("table", e.target.value)}>
            <option value="">Todos</option>
            {catalogs?.tables.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="date_from">Desde</label>
          <br />
          <input id="date_from" type="date" value={filters.date_from} max={filters.date_to || undefined} onChange={(e) => set("date_from", e.target.value)} />
        </p>
        <p>
          <label htmlFor="date_to">Hasta</label>
          <br />
          <input id="date_to" type="date" value={filters.date_to} min={filters.date_from || undefined} onChange={(e) => set("date_to", e.target.value)} />
        </p>
        <p className="audit-buttons">
          <button type="submit">Buscar</button>{" "}
          <button type="button" onClick={handleClear}>Limpiar</button>
        </p>
      </form>
      <div className="list-actions">
        <ExportButton path="bitacora/" params={{ ...applied }} label="Exportar a PDF (las 2000 líneas más recientes)" />
      </div>

      {loadError && <p role="alert">{loadError}</p>}
      {data && (
        <p role="status">
          {data.total === 0 ? "Sin resultados." : `${data.total} ${data.total === 1 ? "registro" : "registros"}.`}
        </p>
      )}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Fecha y hora</th>
              <th>Usuario</th>
              <th>Acción</th>
              <th>Registro</th>
              <th>Cambios</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 && (
              <tr>
                <td colSpan={5}>No hay movimientos.</td>
              </tr>
            )}
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td>{formatTime(entry.timestamp)}</td>
                <td>
                  {entry.enrollment_id ? (
                    <>
                      {entry.enrollment_id}
                      {entry.user_name && <div className="hint">{entry.user_name}{entry.role ? ` · ${entry.role}` : ""}</div>}
                    </>
                  ) : (
                    entry.user_name || "—"
                  )}
                </td>
                <td>{entry.action_label}</td>
                <td>
                  {entry.table_label ? (
                    <>
                      <strong>{entry.table_label}</strong>
                      <div className="hint">{entry.record}</div>
                    </>
                  ) : (
                    "—"
                  )}
                </td>
                <td>
                  <Changes entry={entry} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.pages > 1 && (
        <p className="audit-pager">
          <button type="button" disabled={data.page <= 1} onClick={() => load(applied, data.page - 1)}>
            Anterior
          </button>{" "}
          Página {data.page} de {data.pages}{" "}
          <button type="button" disabled={data.page >= data.pages} onClick={() => load(applied, data.page + 1)}>
            Siguiente
          </button>
        </p>
      )}
    </main>
  );
}
