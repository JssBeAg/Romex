"use client";

import { FormEvent, useEffect, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import Avatar from "@/components/Avatar";
import SortHeader from "@/components/SortHeader";
import { useList } from "@/lib/listing";
import Link from "next/link";
import { useManagerGuard } from "@/lib/useManagerGuard";
import { type Option } from "@/lib/http";
import { type Worker, deleteWorker, getCatalogs, listWorkers } from "@/lib/workers";

export default function WorkersPage() {
  const { loading, allowed } = useManagerGuard();
  const [search, setSearch] = useState("");
  const [roles, setRoles] = useState<Option[]>([]);
  const [message, setMessage] = useState("");
  const [deleteError, setDeleteError] = useState(""); // why a delete failed

  const list = useList({
    fetch: listWorkers,
    rows: (data) => data.workers,
    initial: { order: "enrollment_id" },
    enabled: allowed,
  });
  const workers = list.page.items;
  const { params } = list;


  useEffect(() => {
    if (!allowed) return;
    getCatalogs().then((res) => {
      if (res.ok && res.data) setRoles(res.data.roles);
    });
  }, [allowed]);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    list.update({ q: search.trim() });
  }

  async function handleDelete(worker: Worker) {
    const name = `${worker.first_name} ${worker.paternal_surname}`;
    if (!window.confirm(`¿Eliminar a ${name} (${worker.enrollment_id})? Esta acción no se puede deshacer.`)) {
      return;
    }
    const res = await deleteWorker(worker.id);
    if (res.ok) {
      setMessage(`Se eliminó a ${name}.`);
      list.reload();
    } else {
      setMessage("");
      setDeleteError(res.error ?? "No se pudo eliminar al trabajador.");
    }
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Trabajadores</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Trabajadores</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={handleSearch}>
        <label htmlFor="search">Buscar (matrícula o nombre)</label>{" "}
        <input id="search" value={search} onChange={(e) => setSearch(e.target.value)} />{" "}
        <label htmlFor="role_id">Rol</label>{" "}
        <select id="role_id" value={String(params.role_id ?? "")} onChange={(e) => list.update({ role_id: e.target.value })}>
          <option value="">Todos</option>
          {roles.map((role) => (
            <option key={role.id} value={role.id}>
              {role.label}
            </option>
          ))}
        </select>{" "}
        <label htmlFor="status">Mostrar</label>{" "}
        <select id="status" value={String(params.status ?? "")} onChange={(e) => list.update({ status: e.target.value })}>
          <option value="">Todos</option>
          <option value="active">Activos</option>
          <option value="inactive">Inactivos</option>
        </select>{" "}
        <button type="submit">Buscar</button>
      </form>

      <p>
        <Link className="button-link" href="/trabajadores/nuevo">Nuevo trabajador</Link>
      </p>

      <div className="list-actions">
        <ExportButton path="trabajadores/" params={params} />
      </div>

      {message && <p role="status">{message}</p>}
      {deleteError && (
        <ErrorDialog title="No se pudo eliminar" messages={[deleteError]} onClose={() => setDeleteError("")} />
      )}
      {list.error && <p role="alert">{list.error}</p>}

      <div className="table-scroll"><table>
        <thead>
          <tr>
            <SortHeader column="enrollment_id" order={String(params.order)} onSort={list.sortBy}>Matrícula</SortHeader>
            <SortHeader column="name" order={String(params.order)} onSort={list.sortBy}>Nombre</SortHeader>
            <SortHeader column="role" order={String(params.order)} onSort={list.sortBy}>Rol</SortHeader>
            <th>Correo</th>
            <th>Teléfono</th>
            <SortHeader column="is_active" order={String(params.order)} onSort={list.sortBy}>Activo</SortHeader>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {workers.length === 0 && (
            <tr>
              <td colSpan={7}>No hay trabajadores.</td>
            </tr>
          )}
          {workers.map((worker) => (
            <tr key={worker.id}>
              <td>{worker.enrollment_id}</td>
              <td>
                <span className="person-cell">
                  <Avatar
                    size="sm"
                    firstName={worker.first_name}
                    paternalSurname={worker.paternal_surname}
                    enrollmentId={worker.enrollment_id}
                    photoUrl={worker.photo_url}
                  />
                  <span>
                    {worker.first_name} {worker.paternal_surname} {worker.maternal_surname}
                  </span>
                </span>
              </td>
              <td>{worker.role?.label ?? "-"}</td>
              <td>{worker.email}</td>
              <td>
                {worker.phone_display}
                {worker.contacts.length > 0 && (
                  <ul className="contact-list">
                    {worker.contacts.map((contact) => (
                      <li key={contact.id}>
                        <span className="hint">{contact.label}:</span> {contact.display}
                        {contact.contact_name && <span className="hint"> ({contact.contact_name})</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </td>
              <td>
                {worker.is_active ? "Sí" : "No"}
                {worker.locked && <> <span className="stock-low">Bloqueada</span></>}
              </td>
              <td>
                <Link href={`/trabajadores/${worker.id}`}>Editar</Link>{" "}
                <button type="button" onClick={() => handleDelete(worker)}>
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
