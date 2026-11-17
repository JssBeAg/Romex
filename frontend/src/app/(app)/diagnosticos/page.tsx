"use client";

import { FormEvent, useEffect, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import Link from "next/link";
import { type Diagnosis, deleteDiagnosis, listDiagnoses } from "@/lib/diagnoses";
import { MANAGER_ROLE, MECHANIC_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE];

export default function DiagnosesPage() {
  const { loading, allowed, user } = useRoleGuard(ALLOWED_ROLES);
  const isMechanic = user?.role === MECHANIC_ROLE;
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState(""); // why a delete failed

  const list = useList({
    fetch: listDiagnoses,
    rows: (data) => data.diagnoses,
    initial: { order: "-date" },
    enabled: allowed,
  });
  const diagnoses = list.page.items;
  const { params } = list;


  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(diagnosis: Diagnosis) {
    if (!window.confirm(`¿Eliminar ${diagnosis.title}? Esta acción no se puede deshacer.`)) return;
    const res = await deleteDiagnosis(diagnosis.id);
    if (res.ok) {
      setMessage(`Se eliminó: ${diagnosis.title}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar el diagnóstico.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Diagnósticos</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{isMechanic ? "Mis diagnósticos" : "Diagnósticos"}</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (número económico, placa o causa)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label htmlFor="date_from">Desde</label>{" "}
        <input id="date_from" type="date" value={String(params.date_from ?? "")} onChange={(e) => list.update({ date_from: e.target.value })} />{" "}
        <label htmlFor="date_to">Hasta</label>{" "}
        <input id="date_to" type="date" value={String(params.date_to ?? "")} onChange={(e) => list.update({ date_to: e.target.value })} />{" "}
        <button type="submit">Buscar</button>
      </form>

      {isMechanic && (
        <p>
          <Link className="button-link" href="/diagnosticos/nuevo">Nuevo diagnóstico</Link>
        </p>
      )}

      <div className="list-actions">
        <ExportButton path="diagnosticos/" params={params} />
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
            <th>Reporte</th>
            <SortHeader column="severity" order={String(params.order)} onSort={list.sortBy}>Gravedad</SortHeader>
            <th>Requiere reparación</th>
            <th>Unidad operable</th>
            {!isMechanic && <SortHeader column="diagnosed_by" order={String(params.order)} onSort={list.sortBy}>Diagnosticó</SortHeader>}
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {diagnoses.length === 0 && (
            <tr>
              <td colSpan={isMechanic ? 7 : 8}>No hay diagnósticos.</td>
            </tr>
          )}
          {diagnoses.map((diagnosis) => (
            <tr key={diagnosis.id}>
              <td>{diagnosis.date}</td>
              <td>{diagnosis.unit.label}</td>
              <td>{diagnosis.fault_report.title}</td>
              <td>{diagnosis.severity.label}</td>
              <td>{diagnosis.requires_repair ? "Sí" : "No"}</td>
              <td>{diagnosis.unit_operable ? "Sí" : "No"}</td>
              {!isMechanic && <td>{diagnosis.diagnosed_by.label}</td>}
              <td>
                <Link href={`/diagnosticos/${diagnosis.id}`}>{diagnosis.can_modify ? "Editar" : "Ver"}</Link>
                {diagnosis.can_modify && (
                  <>
                    {" "}
                    <button type="button" onClick={() => handleDelete(diagnosis)}>
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
