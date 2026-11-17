"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import { MANAGER_ROLE } from "@/lib/roles";
import { type Plan, deletePlan, listPlans } from "@/lib/preventive";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

export default function PlansPage() {
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const [search, setSearch] = useState("");
  const list = useList({
    fetch: listPlans,
    rows: (data) => data.plans,
    initial: { order: "name", status: "active" },
    enabled: allowed,
  });
  const plans = list.page.items;
  const { params } = list;

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(plan: Plan) {
    if (!window.confirm(`¿Eliminar ${plan.name}? Esta acción no se puede deshacer.`)) return;
    const res = await deletePlan(plan.id);
    if (res.ok) {
      setMessage(`Se eliminó: ${plan.name}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar el plan.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Planes preventivos</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Planes preventivos</h1>
      <p>
        <Link className="back-link" href="/preventivo">Volver a mantenimiento preventivo</Link>
      </p>
      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (nombre o descripción)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label htmlFor="status">Mostrar</label>{" "}
        <select id="status" value={String(params.status ?? "all")} onChange={(e) => list.update({ status: e.target.value })}>
          <option value="active">Activos</option>
          <option value="inactive">Inactivos</option>
          <option value="all">Todos</option>
        </select>{" "}
        <button type="submit">Buscar</button>
      </form>

      <div className="list-actions">
        <Link className="button-link" href="/preventivo/planes/nuevo">Nuevo plan</Link>
        <ExportButton path="preventivo/planes/" params={params} />
      </div>

      {message && <p role="status">{message}</p>}
      {deleteError && (
        <ErrorDialog title="No se pudo eliminar" messages={[deleteError]} onClose={() => setDeleteError("")} />
      )}
      {list.error && <p role="alert">{list.error}</p>}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <SortHeader column="name" order={String(params.order)} onSort={list.sortBy}>Plan</SortHeader>
              <th>Se repite</th>
              <th>Aplica a</th>
              <SortHeader column="is_active" order={String(params.order)} onSort={list.sortBy}>Estado</SortHeader>
              <th>Servicios</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {plans.length === 0 && (
              <tr>
                <td colSpan={6}>No hay planes.</td>
              </tr>
            )}
            {plans.map((plan) => (
              <tr key={plan.id}>
                <td>{plan.name}</td>
                <td>
                  {[plan.every_km ? `cada ${plan.every_km.toLocaleString("es-MX")} km` : "", plan.every_days ? `cada ${plan.every_days} días` : ""]
                    .filter(Boolean)
                    .join(" o ")}
                </td>
                <td>{plan.unit_model ? plan.unit_model.label : "Todas las unidades"}</td>
                <td>{plan.is_active ? "Activo" : "Inactivo"}</td>
                <td>{plan.services}</td>
                <td>
                  <Link href={`/preventivo/planes/${plan.id}`}>Editar</Link>{" "}
                  {plan.can_delete && (
                    <button type="button" onClick={() => handleDelete(plan)}>
                      Eliminar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination
        pagination={list.page.pagination}
        onPage={(page) => list.update({ page })}
        onPageSize={(size) => list.update({ page_size: size })}
      />
    </main>
  );
}
