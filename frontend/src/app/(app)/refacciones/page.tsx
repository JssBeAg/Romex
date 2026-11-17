"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import PartPhoto from "@/components/PartPhoto";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import { MANAGER_ROLE } from "@/lib/roles";
import { type SparePart, deleteSparePart, listSpareParts } from "@/lib/spareParts";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

export default function SparePartsPage() {
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const list = useList({
    fetch: listSpareParts,
    rows: (data) => data.spare_parts,
    initial: { order: "name", status: "active" },
    enabled: allowed,
  });
  const parts = list.page.items;
  const { params } = list;
  const lowCount = list.page.data?.low_stock_count ?? 0;
  const lowOnly = params.low === true;

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(part: SparePart) {
    if (!window.confirm(`¿Eliminar ${part.name}? Esta acción no se puede deshacer.`)) return;
    const res = await deleteSparePart(part.id);
    if (res.ok) {
      setMessage(`Se eliminó: ${part.name}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar la refacción.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Refacciones</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Refacciones</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (nombre o descripción)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label>
          <input type="checkbox" checked={lowOnly} onChange={(e) => list.update({ low: e.target.checked })} /> Solo stock bajo
        </label>{" "}
        <label htmlFor="status">Mostrar</label>{" "}
        <select id="status" value={String(params.status ?? "all")} onChange={(e) => list.update({ status: e.target.value })}>
          <option value="active">Activas</option>
          <option value="inactive">Inactivas</option>
          <option value="all">Todas</option>
        </select>{" "}
        <button type="submit">Buscar</button>
      </form>

      <p>
        <Link className="button-link" href="/refacciones/nueva">Nueva refacción</Link>
      </p>

      {lowCount > 0 && !lowOnly && (
        <p role="status" className="stock-warning">
          {lowCount} {lowCount === 1 ? "refacción tiene" : "refacciones tienen"} stock bajo.
        </p>
      )}
      <div className="list-actions">
        <ExportButton path="refacciones/" params={params} />
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
              <SortHeader column="name" order={String(params.order)} onSort={list.sortBy}>Nombre</SortHeader>
              <SortHeader column="stock" order={String(params.order)} onSort={list.sortBy}>Existencias</SortHeader>
              <SortHeader column="min_stock" order={String(params.order)} onSort={list.sortBy}>Mínimo</SortHeader>
              <SortHeader column="price" order={String(params.order)} onSort={list.sortBy}>Precio de referencia</SortHeader>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {parts.length === 0 && (
              <tr>
                <td colSpan={5}>No hay refacciones.</td>
              </tr>
            )}
            {parts.map((part) => (
              <tr key={part.id}>
                <td>
                  <span className="person-cell">
                    <PartPhoto photoUrl={part.photo_url} />
                    <span>{part.name}</span>
                  </span>
                </td>
                <td>
                  {part.stock}
                  {part.low_stock && <span className="stock-low">Stock bajo</span>}
                  {!part.is_active && <> <span className="stock-low">Inactiva</span></>}
                </td>
                <td>{part.min_stock}</td>
                <td>{part.unit_price === null ? "—" : `$${part.unit_price}`}</td>
                <td>
                  <Link href={`/refacciones/${part.id}`}>Ver / Editar</Link>{" "}
                  {part.can_delete && (
                    <button type="button" onClick={() => handleDelete(part)}>
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
