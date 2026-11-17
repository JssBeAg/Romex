"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { MANAGER_ROLE, MECHANIC_ROLE } from "@/lib/roles";
import { type DueRow, type DueStatus, type DueSummary, getDue } from "@/lib/preventive";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE];

const BADGE: Record<DueStatus, string> = {
  vencido: "overdue",
  proximo: "upcoming",
  al_corriente: "ok",
  sin_historial: "no_history",
};

const CARDS: { status: DueStatus; key: keyof DueSummary; label: string }[] = [
  { status: "vencido", key: "overdue", label: "Vencidos" },
  { status: "proximo", key: "upcoming", label: "Próximos" },
  { status: "sin_historial", key: "no_history", label: "Sin historial" },
  { status: "al_corriente", key: "ok", label: "Al corriente" },
];

export default function PreventivePage() {
  const { loading, allowed, user } = useRoleGuard(ALLOWED_ROLES);
  const [rows, setRows] = useState<DueRow[]>([]);
  const [summary, setSummary] = useState<DueSummary | null>(null);
  const [status, setStatus] = useState<DueStatus | "">("");
  const [search, setSearch] = useState("");
  const [loadError, setLoadError] = useState("");

  const load = useCallback(async (current: string, query: string) => {
    const res = await getDue(current, query);
    if (res.ok && res.data) {
      setRows(res.data.rows);
      setSummary(res.data.summary);
      setLoadError("");
    } else {
      setLoadError(res.error ?? "No se pudo cargar la lista");
    }
  }, []);

  useEffect(() => {
    if (allowed) load("", "");
  }, [allowed, load]);

  function pick(next: DueStatus) {
    const value = status === next ? "" : next; // a second click clears the filter
    setStatus(value);
    load(value, search);
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    load(status, search);
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Mantenimiento preventivo</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  const isManager = user?.role === MANAGER_ROLE;

  return (
    <main>
      <h1>Mantenimiento preventivo</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>
      <p className="hint">
        Cada unidad contra cada plan: vence por kilómetros o por días, lo que ocurra primero. El conteo se
        reinicia al registrar un mantenimiento preventivo que cumpla el plan.
      </p>
      <p>
        {isManager && <Link className="button-link" href="/preventivo/planes">Administrar planes</Link>}{" "}
        {user?.role === MECHANIC_ROLE && (
          <Link className="button-link" href="/mantenimientos/nuevo">Registrar mantenimiento</Link>
        )}{" "}
        <ExportButton path="preventivo/vencimientos/" params={{ status, q: search }} />
      </p>

      {summary && (
        <div className="summary-cards">
          {CARDS.map((card) => (
            <button
              key={card.status}
              type="button"
              className={`summary-card${status === card.status ? " selected" : ""}`}
              onClick={() => pick(card.status)}
              aria-pressed={status === card.status}
            >
              <strong>{summary[card.key]}</strong>
              <span>{card.label}</span>
            </button>
          ))}
        </div>
      )}

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (unidad o plan)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <button type="submit">Buscar</button>
      </form>

      {loadError && <p role="alert">{loadError}</p>}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Unidad</th>
              <th>Plan</th>
              <th>Estado</th>
              <th>Detalle</th>
              <th>Último servicio</th>
              <th>Km actuales</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>No hay resultados.</td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={`${row.unit.id}-${row.plan.id}`}>
                <td>{row.unit.label}</td>
                <td>{row.plan.name}</td>
                <td>
                  <span className={`status-badge ${BADGE[row.status]}`}>{row.status_label}</span>
                </td>
                <td>{row.message}</td>
                <td>{row.last ? `${row.last.date}, ${row.last.mileage} km` : "—"}</td>
                <td>{row.current_mileage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
