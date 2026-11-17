"use client";

import { FormEvent, useEffect, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import Link from "next/link";
import { type Option } from "@/lib/http";
import { MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE } from "@/lib/roles";
import { type Report, deleteReport, getReportCatalogs, listReports } from "@/lib/reports";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE];

export default function ReportsPage() {
  const { loading, allowed, user } = useRoleGuard(ALLOWED_ROLES);
  const isOperator = user?.role === OPERATOR_ROLE;
  const isManager = user?.role === MANAGER_ROLE;
  const isMechanic = user?.role === MECHANIC_ROLE;
  const [statuses, setStatuses] = useState<Option[]>([]);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState(""); // why a delete failed
  const list = useList({
    fetch: listReports,
    rows: (data) => data.reports,
    initial: { order: "-date" },
    enabled: allowed,
  });
  const reports = list.page.items;
  const { params } = list;

  useEffect(() => {
    if (!allowed) return;
    getReportCatalogs().then((res) => {
      if (res.ok && res.data) setStatuses(res.data.statuses);
    });
  }, [allowed]);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(report: Report) {
    if (!window.confirm(`¿Eliminar ${report.title}? Esta acción no se puede deshacer.`)) {
      return;
    }
    const res = await deleteReport(report.id);
    if (res.ok) {
      setMessage(`Se eliminó: ${report.title}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar el reporte.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Reportes de fallas</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{isOperator ? "Mis reportes de fallas" : isMechanic ? "Reportes asignados a mí" : "Reportes de fallas"}</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (número económico, placa o ubicación)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label htmlFor="status">Estatus</label>{" "}
        <select id="status" value={String(params.status_id ?? "")} onChange={(e) => list.update({ status_id: e.target.value })}>
          <option value="">Todos</option>
          {statuses.map((option) => (
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

      <div className="list-actions">
        {isOperator && <Link className="button-link" href="/reportes/nuevo">Nuevo reporte</Link>}
        <ExportButton path="reportes-fallas/" params={params} />
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
            <SortHeader column="unit" order={String(params.order)} onSort={list.sortBy}>Unidad</SortHeader>
            <SortHeader column="location" order={String(params.order)} onSort={list.sortBy}>Ubicación</SortHeader>
            <SortHeader column="status" order={String(params.order)} onSort={list.sortBy}>Estatus</SortHeader>
            {!isOperator && <SortHeader column="reported_by" order={String(params.order)} onSort={list.sortBy}>Reportó</SortHeader>}
            {isManager && <th>Mecánicos</th>}
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {reports.length === 0 && (
            <tr>
              <td colSpan={isOperator ? 5 : isManager ? 7 : 6}>
                {isMechanic ? "No tienes reportes asignados. El gerente te los asignará." : "No hay reportes."}
              </td>
            </tr>
          )}
          {reports.map((report) => (
            <tr key={report.id}>
              <td>{report.date}</td>
              <td>{report.unit.label}</td>
              <td>{report.location}</td>
              <td>{report.status.label}</td>
              {!isOperator && <td>{report.reported_by.label}</td>}
              {isManager && (
                <td>
                  {(report.mechanics ?? [])
                    .filter((a) => a.end_date === null)
                    .map((a) => a.mechanic.label)
                    .join(", ") || "Sin asignar"}
                </td>
              )}
              <td>
                <Link href={`/reportes/${report.id}`}>{report.can_modify ? "Editar" : "Ver"}</Link>
                {report.can_modify && (
                  <>
                    {" "}
                    <button type="button" onClick={() => handleDelete(report)}>
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
