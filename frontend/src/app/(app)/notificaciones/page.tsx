"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ErrorDialog from "@/components/ErrorDialog";
import Pagination from "@/components/Pagination";
import { useList } from "@/lib/listing";
import { type Notification, clearRead, listNotifications, markRead } from "@/lib/notifications";
import { useRoleGuard } from "@/lib/useRoleGuard";
import { MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE } from "@/lib/roles";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE];

function when(iso: string) {
  return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
}

export default function NotificationsPage() {
  const router = useRouter();
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [error, setError] = useState("");
  const list = useList({
    fetch: listNotifications,
    rows: (data) => data.notifications,
    enabled: allowed,
  });
  const { params } = list;
  const unread = list.page.data?.unread ?? 0;
  const kinds = list.page.data?.kinds ?? [];

  // Keep the list fresh while the page is open
  useEffect(() => {
    if (!allowed) return;
    const timer = setInterval(() => list.reload(), 60000);
    return () => clearInterval(timer);
  }, [allowed, list.reload]);

  async function open(n: Notification) {
    if (!n.is_read) await markRead([n.id]);
    if (n.link) router.push(n.link);
    else list.reload();
  }

  async function readAll() {
    const res = await markRead();
    if (!res.ok) setError(res.error ?? "No se pudo marcar como leídas.");
    list.reload();
  }

  async function clear() {
    if (!window.confirm("¿Borrar las notificaciones que ya leíste?")) return;
    const res = await clearRead();
    if (!res.ok) setError(res.error ?? "No se pudieron borrar.");
    list.reload();
  }

  if (loading) return <p>Cargando...</p>;
  if (!allowed) {
    return (
      <main>
        <h1>Notificaciones</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
      </main>
    );
  }

  return (
    <main>
      <h1>Notificaciones</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <form onSubmit={(e) => e.preventDefault()}>
        <label>
          <input type="checkbox" checked={params.unread === true} onChange={(e) => list.update({ unread: e.target.checked })} /> Solo no leídas
        </label>{" "}
        <label htmlFor="kind">Tipo</label>{" "}
        <select id="kind" value={String(params.kind ?? "")} onChange={(e) => list.update({ kind: e.target.value })}>
          <option value="">Todos</option>
          {kinds.map((kind) => (
            <option key={kind.id} value={kind.id}>
              {kind.label}
            </option>
          ))}
        </select>
      </form>

      <div className="list-actions">
        <button type="button" onClick={readAll} disabled={unread === 0}>
          Marcar todas como leídas{unread > 0 ? ` (${unread})` : ""}
        </button>
        <button type="button" onClick={clear}>Borrar las leídas</button>
      </div>

      {list.error && <p role="alert">{list.error}</p>}
      {error && <ErrorDialog title="No se pudo completar" messages={[error]} onClose={() => setError("")} />}

      {list.page.items.length === 0 && !list.loading ? (
        <p>{params.unread === true ? "No tienes notificaciones sin leer." : "No tienes notificaciones."}</p>
      ) : (
        <ul className="notification-list">
          {list.page.items.map((n) => (
            <li key={n.id} className={`notification-item${n.is_read ? "" : " unread"}`}>
              <span>{n.message}</span>
              <span className="notification-meta">
                {n.kind_label} · {when(n.created_at)}
                {n.is_read ? " · Leída" : ""}
              </span>
              <span>
                {n.link && (
                  <button type="button" onClick={() => open(n)}>
                    Ver
                  </button>
                )}{" "}
                {!n.is_read && (
                  <button
                    type="button"
                    onClick={async () => {
                      await markRead([n.id]);
                      list.reload();
                    }}
                  >
                    Marcar como leída
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}

      <Pagination
        pagination={list.page.pagination}
        onPage={(page) => list.update({ page })}
        onPageSize={(size) => list.update({ page_size: size })}
      />
    </main>
  );
}
