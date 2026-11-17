"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { useParams } from "next/navigation";
import { MANAGER_ROLE } from "@/lib/roles";
import { EVENT_LABELS, type Kardex, getKardex } from "@/lib/kardex";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

const money = (value: string) =>
  Number(value).toLocaleString("es-MX", { style: "currency", currency: "MXN" });

export default function KardexPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [kardex, setKardex] = useState<Kardex | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getKardex(id).then((res) => {
      if (res.ok && res.data) setKardex(res.data);
      else setLoadError(res.error ?? "No se pudo cargar el kardex");
    });
  }, [allowed, id]);

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

  const unit = kardex?.unit;
  const s = kardex?.summary;

  return (
    <main>
      <h1>{unit ? `Kardex de la unidad ${unit.economic_number}` : "Kardex"}</h1>
      <p>
        <Link className="back-link" href="/kardex">Volver a la lista</Link>
      </p>
      <div className="list-actions">
        <ExportButton path={`kardex/${id}/`} label="Ver kardex en PDF" />
      </div>
      {loadError && <p role="alert">{loadError}</p>}
      {!kardex && !loadError && <p>Cargando...</p>}

      {kardex && unit && s && (
        <>
          <h2>Datos de la unidad</h2>
          <div className="table-scroll"><table>
            <tbody>
              <tr><th>Número económico</th><td>{unit.economic_number}</td></tr>
              <tr><th>Marca y modelo</th><td>{unit.brand.label} / {unit.unit_model.label}</td></tr>
              <tr>
                <th>Placa actual</th>
                <td>
                  {unit.current_plate
                    ? `${unit.current_plate.identifier} (${unit.current_plate.state})`
                    : "Sin placa vigente"}
                </td>
              </tr>
              <tr><th>Kilometraje actual</th><td>{unit.mileage} km</td></tr>
              <tr>
                <th>Operadores asignados</th>
                <td>
                  {unit.operators
                    .filter((assignment) => assignment.end_date === null)
                    .map((assignment) => assignment.operator.label)
                    .join(", ") || "Sin operadores asignados"}
                </td>
              </tr>
            </tbody>
          </table></div>

          <h2>Resumen</h2>
          <div className="table-scroll"><table>
            <tbody>
              <tr>
                <th>Reportes de fallas</th>
                <td>{s.reports} ({s.pending_reports} abiertos)</td>
              </tr>
              <tr><th>Diagnósticos</th><td>{s.diagnoses}</td></tr>
              <tr>
                <th>Mantenimientos</th>
                <td>
                  {s.maintenances} ({s.preventive_maintenances} preventivos, {s.corrective_maintenances} correctivos)
                </td>
              </tr>
              <tr><th>Costo total de mantenimientos</th><td>{money(s.total_maintenance_cost)}</td></tr>
              <tr>
                <th>Último mantenimiento</th>
                <td>
                  {s.last_maintenance
                    ? `${s.last_maintenance.date} a los ${s.last_maintenance.mileage} km`
                    : "Sin mantenimientos"}
                </td>
              </tr>
              <tr>
                <th>Checklists</th>
                <td>
                  {s.checklists}
                  {s.last_checklist && ` (el último: ${s.last_checklist.date}, ${s.last_checklist.mileage} km)`}
                </td>
              </tr>
            </tbody>
          </table></div>

          <h2>Mantenimiento preventivo</h2>
          {kardex.preventive.length === 0 ? (
            <p>No hay planes preventivos activos para esta unidad.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Plan</th>
                    <th>Estado</th>
                    <th>Detalle</th>
                    <th>Último servicio</th>
                  </tr>
                </thead>
                <tbody>
                  {kardex.preventive.map((row) => (
                    <tr key={row.plan.id}>
                      <td>{row.plan.name}</td>
                      <td><span className={`status-badge ${row.status === "vencido" ? "overdue" : row.status === "proximo" ? "upcoming" : row.status === "al_corriente" ? "ok" : "no_history"}`}>{row.status_label}</span></td>
                      <td>{row.message}</td>
                      <td>{row.last ? `${row.last.date}, ${row.last.mileage} km` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h2>Refacciones cambiadas</h2>
          {kardex.parts_used.length === 0 ? (
            <p>A esta unidad todavía no se le ha cambiado ninguna refacción.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Refacción</th>
                    <th>Piezas</th>
                    <th>Veces</th>
                    <th>Último cambio</th>
                  </tr>
                </thead>
                <tbody>
                  {kardex.parts_used.map((part) => (
                    <tr key={part.id}>
                      <td>{part.label}</td>
                      <td>{part.pieces}</td>
                      <td>{part.times}</td>
                      <td>{part.last_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h2>Historial</h2>
          <div className="table-scroll"><table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Registro</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {kardex.events.length === 0 && (
                <tr>
                  <td colSpan={4}>Esta unidad todavía no tiene historial.</td>
                </tr>
              )}
              {kardex.events.map((event, index) => (
                <tr key={`${event.type}-${index}`}>
                  <td>{event.date}</td>
                  <td>{EVENT_LABELS[event.type]}</td>
                  <td>{event.link ? <Link href={event.link}>{event.title}</Link> : event.title}</td>
                  <td style={{ whiteSpace: "pre-line" }}>{event.detail}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </>
      )}
    </main>
  );
}
