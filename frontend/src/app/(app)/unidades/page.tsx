"use client";

import { FormEvent, useEffect, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import Link from "next/link";
import { useManagerGuard } from "@/lib/useManagerGuard";
import { type Unit, deleteUnit, listUnits } from "@/lib/units";

export default function UnitsPage() {
  const { loading, allowed } = useManagerGuard();
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState(""); // why a delete failed

  const list = useList({
    fetch: listUnits,
    rows: (data) => data.units,
    initial: { order: "economic_number", status: "active" },
    enabled: allowed,
  });
  const units = list.page.items;
  const { params } = list;


  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(unit: Unit) {
    const name = unit.economic_number;
    if (!window.confirm(`¿Eliminar la unidad ${name}? Esta acción no se puede deshacer.`)) {
      return;
    }
    const res = await deleteUnit(unit.id);
    if (res.ok) {
      setMessage(`Se eliminó la unidad ${name}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar la unidad.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Unidades</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Unidades</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (número económico o placa)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label htmlFor="status">Mostrar</label>{" "}
        <select id="status" value={String(params.status ?? "all")} onChange={(e) => list.update({ status: e.target.value })}>
          <option value="active">Activas</option>
          <option value="inactive">Inactivas</option>
          <option value="all">Todas</option>
        </select>{" "}
        <button type="submit">Buscar</button>
      </form>

      <p>
        <Link className="button-link" href="/unidades/nueva">Nueva unidad</Link>
      </p>

      <div className="list-actions">
        <ExportButton path="unidades/" params={params} />
      </div>

      {message && <p role="status">{message}</p>}
      {deleteError && (
        <ErrorDialog title="No se pudo eliminar" messages={[deleteError]} onClose={() => setDeleteError("")} />
      )}
      {list.error && <p role="alert">{list.error}</p>}

      <div className="table-scroll"><table>
        <thead>
          <tr>
            <SortHeader column="economic_number" order={String(params.order)} onSort={list.sortBy}>Número económico</SortHeader>
            <th>Placa actual</th>
            <th>Estado de la placa</th>
            <SortHeader column="brand" order={String(params.order)} onSort={list.sortBy}>Marca</SortHeader>
            <SortHeader column="model" order={String(params.order)} onSort={list.sortBy}>Modelo</SortHeader>
            <SortHeader column="mileage" order={String(params.order)} onSort={list.sortBy}>Kilometraje</SortHeader>
            <th>Operador</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {units.length === 0 && (
            <tr>
              <td colSpan={8}>No hay unidades.</td>
            </tr>
          )}
          {units.map((unit) => (
            <tr key={unit.id}>
              <td>
                {unit.economic_number}
                {!unit.is_active && <> <span className="stock-low">Inactiva</span></>}
              </td>
              <td>{unit.current_plate?.identifier ?? "Sin placa vigente"}</td>
              <td>{unit.current_plate?.state ?? "-"}</td>
              <td>{unit.brand.label}</td>
              <td>{unit.unit_model.label}</td>
              <td>{unit.mileage}</td>
              <td>
                {unit.current_operator?.operator.label ?? "Sin asignar"}
              </td>
              <td>
                <Link href={`/unidades/${unit.id}`}>Editar</Link>{" "}
                <button type="button" onClick={() => handleDelete(unit)}>
                  Eliminar
                </button>
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
