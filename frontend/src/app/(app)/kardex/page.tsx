"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import { MANAGER_ROLE } from "@/lib/roles";
import { type Unit, listUnits } from "@/lib/units";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

export default function KardexListPage() {
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [search, setSearch] = useState("");

  const list = useList({
    fetch: listUnits,
    rows: (data) => data.units,
    initial: { order: "economic_number" },
    enabled: allowed,
  });
  const units = list.page.items;
  const { params } = list;


  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Kardex</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Kardex</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>
      <p>Elige una unidad para ver su historial.</p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (número económico o placa)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <button type="submit">Buscar</button>
      </form>

      <div className="list-actions">
        <ExportButton path="unidades/" params={params} label="Exportar lista de unidades" />
      </div>

      {list.error && <p role="alert">{list.error}</p>}

      <div className="table-scroll"><table>
        <thead>
          <tr>
            <SortHeader column="economic_number" order={String(params.order)} onSort={list.sortBy}>Número económico</SortHeader>
            <th>Placa actual</th>
            <SortHeader column="brand" order={String(params.order)} onSort={list.sortBy}>Marca</SortHeader>
            <SortHeader column="model" order={String(params.order)} onSort={list.sortBy}>Modelo</SortHeader>
            <SortHeader column="mileage" order={String(params.order)} onSort={list.sortBy}>Kilometraje</SortHeader>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {units.length === 0 && (
            <tr>
              <td colSpan={6}>No hay unidades.</td>
            </tr>
          )}
          {units.map((unit) => (
            <tr key={unit.id}>
              <td>
                {unit.economic_number}
                {!unit.is_active && <> <span className="stock-low">Inactiva</span></>}
              </td>
              <td>{unit.current_plate?.identifier ?? "Sin placa vigente"}</td>
              <td>{unit.brand.label}</td>
              <td>{unit.unit_model.label}</td>
              <td>{unit.mileage}</td>
              <td>
                <Link href={`/kardex/${unit.id}`}>Ver kardex</Link>
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
