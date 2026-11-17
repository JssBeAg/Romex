"use client";

import { FormEvent, useEffect, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import Link from "next/link";
import { MANAGER_ROLE, OPERATOR_ROLE } from "@/lib/roles";
import { type Checklist, deleteChecklist, listChecklists, yesNo } from "@/lib/checklists";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, OPERATOR_ROLE];

export default function ChecklistsPage() {
  const { loading, allowed, user } = useRoleGuard(ALLOWED_ROLES);
  const isOperator = user?.role === OPERATOR_ROLE;
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState(""); // why a delete failed

  const list = useList({
    fetch: listChecklists,
    rows: (data) => data.checklists,
    initial: { order: "-date" },
    enabled: allowed,
  });
  const checklists = list.page.items;
  const { params } = list;


  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(checklist: Checklist) {
    if (!window.confirm(`¿Eliminar ${checklist.title}? Esta acción no se puede deshacer.`)) return;
    const res = await deleteChecklist(checklist.id);
    if (res.ok) {
      setMessage(`Se eliminó: ${checklist.title}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar el checklist.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Checklists</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{isOperator ? "Mis checklists" : "Checklists"}</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (número económico, placa o descripción)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label htmlFor="date_from">Desde</label>{" "}
        <input id="date_from" type="date" value={String(params.date_from ?? "")} onChange={(e) => list.update({ date_from: e.target.value })} />{" "}
        <label htmlFor="date_to">Hasta</label>{" "}
        <input id="date_to" type="date" value={String(params.date_to ?? "")} onChange={(e) => list.update({ date_to: e.target.value })} />{" "}
        <label>
          <input type="checkbox" checked={params.problems === true} onChange={(e) => list.update({ problems: e.target.checked })} /> Solo con problemas
        </label>{" "}
        <button type="submit">Buscar</button>
      </form>

      {isOperator && (
        <p>
          <Link className="button-link" href="/checklists/nuevo">Nuevo checklist</Link>
        </p>
      )}

      <div className="list-actions">
        <ExportButton path="checklists/" params={params} />
      </div>

      {message && <p role="status">{message}</p>}
      {deleteError && (
        <ErrorDialog title="No se pudo eliminar" messages={[deleteError]} onClose={() => setDeleteError("")} />
      )}
      {list.error && <p role="alert">{list.error}</p>}

      <div className="table-scroll"><table>
        <thead>
          <tr>
            <th>Folio</th>
            <SortHeader column="date" order={String(params.order)} onSort={list.sortBy}>Fecha</SortHeader>
            <SortHeader column="unit" order={String(params.order)} onSort={list.sortBy}>Unidad</SortHeader>
            <SortHeader column="mileage" order={String(params.order)} onSort={list.sortBy}>Km</SortHeader>
            <th>Luces</th>
            <th>Fluidos</th>
            <th>Sin grietas</th>
            {!isOperator && <SortHeader column="completed_by" order={String(params.order)} onSort={list.sortBy}>Registró</SortHeader>}
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {checklists.length === 0 && (
            <tr>
              <td colSpan={isOperator ? 8 : 9}>No hay checklists.</td>
            </tr>
          )}
          {checklists.map((checklist) => (
            <tr key={checklist.id}>
              <td>{checklist.folio}</td>
              <td>{checklist.date}</td>
              <td>{checklist.unit.label}</td>
              <td>{checklist.recorded_mileage}</td>
              <td>{yesNo(checklist.lights_ok)}</td>
              <td>{yesNo(checklist.fluids_ok)}</td>
              <td>{yesNo(checklist.no_cracks)}</td>
              {!isOperator && <td>{checklist.completed_by.label}</td>}
              <td>
                <Link href={`/checklists/${checklist.id}`}>{checklist.can_modify ? "Editar" : "Ver"}</Link>
                {checklist.can_modify && (
                  <>
                    {" "}
                    <button type="button" onClick={() => handleDelete(checklist)}>
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
