"use client";

import { FormEvent, useEffect, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import Link from "next/link";
import { getMaintenanceCatalogs, deleteMaintenance, listMaintenances, type Maintenance } from "@/lib/maintenances";
import { type Option } from "@/lib/http";
import { MANAGER_ROLE, MECHANIC_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE];

export default function MaintenancesPage() {
  const { loading, allowed, user } = useRoleGuard(ALLOWED_ROLES);
  const isMechanic = user?.role === MECHANIC_ROLE;
  const [serviceTypes, setServiceTypes] = useState<Option[]>([]);
  const [search, setSearch] = useState("");
  const [typeId, setTypeId] = useState("");
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState(""); // why a delete failed

  const list = useList({
    fetch: listMaintenances,
    rows: (data) => data.maintenances,
    initial: { order: "-date" },
    enabled: allowed,
  });
  const maintenances = list.page.items;
  const { params } = list;

  useEffect(() => {
    if (!allowed) return;
    getMaintenanceCatalogs().then((res) => {
      if (res.ok && res.data) setServiceTypes(res.data.service_types);
    });
  }, [allowed]);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(maintenance: Maintenance) {
    if (!window.confirm(`¿Eliminar ${maintenance.title}? Esta acción no se puede deshacer.`)) return;
    const res = await deleteMaintenance(maintenance.id);
    if (res.ok) {
      setMessage(`Se eliminó: ${maintenance.title}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar el mantenimiento.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Mantenimientos</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{isMechanic ? "Mis mantenimientos" : "Mantenimientos"}</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (número económico, placa u observaciones)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label htmlFor="type">Tipo</label>{" "}
        <select id="type" value={typeId} onChange={(e) => setTypeId(e.target.value)}>
          <option value="">Todos</option>
          {serviceTypes.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>{" "}
        <label htmlFor="date_from">Desde</label>{" "}
        <input id="date_from" type="date" value={String(params.date_from ?? "")} onChange={(e) => list.update({ date_from: e.target.value })} />{" "}
        <label htmlFor="date_to">Hasta</label>{" "}
        <input id="date_to" type="date" value={String(params.date_to ?? "")} onChange={(e) => list.update({ date_to: e.target.value })} />{" "}
        <button type="submit">Buscar</button>
      </form>

      {isMechanic && (
        <p>
          <Link className="button-link" href="/mantenimientos/nuevo">Nuevo mantenimiento</Link>
        </p>
      )}

      <div className="list-actions">
        <ExportButton path="mantenimientos/" params={params} />
      </div>

      {message && <p role="status">{message}</p>}
      {deleteError && (
        <ErrorDialog title="No se pudo eliminar" messages={[deleteError]} onClose={() => setDeleteError("")} />
      )}
      {list.error && <p role="alert">{list.error}</p>}

      <div className="table-scroll"><table>
        <thead>
          <tr>
            <SortHeader column="date" order={String(params.order)} onSort={list.sortBy}>Fecha</SortHeader>
            <SortHeader column="service_type" order={String(params.order)} onSort={list.sortBy}>Tipo</SortHeader>
            <SortHeader column="unit" order={String(params.order)} onSort={list.sortBy}>Unidad</SortHeader>
            <SortHeader column="mileage" order={String(params.order)} onSort={list.sortBy}>Km de servicio</SortHeader>
            <SortHeader column="cost" order={String(params.order)} onSort={list.sortBy}>Costo total</SortHeader>
            <th>Realizado por</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {maintenances.length === 0 && (
            <tr>
              <td colSpan={7}>No hay mantenimientos.</td>
            </tr>
          )}
          {maintenances.map((maintenance) => (
            <tr key={maintenance.id}>
              <td>{maintenance.date}</td>
              <td>{maintenance.service_type.label}</td>
              <td>{maintenance.unit.label}</td>
              <td>{maintenance.service_mileage}</td>
              <td>{maintenance.total_cost}</td>
              <td>{maintenance.operators.map((o) => o.label).join(", ")}</td>
              <td>
                <Link href={`/mantenimientos/${maintenance.id}`}>{maintenance.can_modify ? "Editar" : "Ver"}</Link>
                {maintenance.can_modify && (
                  <>
                    {" "}
                    <button type="button" onClick={() => handleDelete(maintenance)}>
                      Eliminar
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table></div>
      <Pagination
        pagination={list.page.pagination}
        onPage={(page) => list.update({ page })}
        onPageSize={(size) => list.update({ page_size: size })}
      />
    </main>
  );
}
