"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { useParams } from "next/navigation";
import SparePartForm from "@/components/SparePartForm";
import StockMovementForm from "@/components/StockMovementForm";
import { MANAGER_ROLE } from "@/lib/roles";
import { type SparePart, getSparePart, updateSparePart } from "@/lib/spareParts";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

export default function SparePartPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [part, setPart] = useState<SparePart | null>(null);
  const [loadError, setLoadError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!allowed) return;
    getSparePart(id).then((res) => {
      if (res.ok && res.data) setPart(res.data.spare_part);
      else setLoadError(res.error ?? "No se pudo cargar la refacción");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Refacción</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{part?.name ?? "Refacción"}</h1>
      <p>
        <Link className="back-link" href="/refacciones">Volver a la lista</Link>
      </p>
      <div className="list-actions">
        <ExportButton path={`refacciones/${id}/`} label="Ver ficha en PDF" />
      </div>
      {loadError && <p role="alert">{loadError}</p>}
      {!part && !loadError && <p>Cargando...</p>}

      {part && (
        <>
          <p>
            Existencias: <strong>{part.stock}</strong> piezas
            {part.low_stock && <span className="stock-low">Stock bajo</span>} · Mínimo: {part.min_stock} · Usadas en
            mantenimientos: {part.used}
          </p>
          {saved && <p role="status">Se guardaron los cambios.</p>}

          <SparePartForm
            part={part}
            onSubmit={(input) => updateSparePart(id, input)}
            onSaved={(updated) => {
              setPart((previous) => ({ ...updated, history: previous?.history }));
              setSaved(true);
            }}
            onCancel={() => history.back()}
          />

          <StockMovementForm partId={id} onSaved={(updated) => { setPart(updated); setSaved(false); }} />

          <section aria-labelledby="history-title">
            <h2 id="history-title">Historial de existencias</h2>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Movimiento</th>
                    <th>Piezas</th>
                    <th>Quedaron</th>
                    <th>Detalle</th>
                    <th>Lo registró</th>
                  </tr>
                </thead>
                <tbody>
                  {(part.history ?? []).length === 0 && (
                    <tr>
                      <td colSpan={6}>Sin movimientos.</td>
                    </tr>
                  )}
                  {(part.history ?? []).map((event) => (
                    <tr key={`${event.kind}-${event.id}`}>
                      <td>{event.date}</td>
                      <td>{event.link ? <Link href={event.link}>{event.kind}</Link> : event.kind}</td>
                      <td>{event.change > 0 ? `+${event.change}` : event.change}</td>
                      <td>{event.balance}</td>
                      <td>{event.detail || "—"}</td>
                      <td>{event.who}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
