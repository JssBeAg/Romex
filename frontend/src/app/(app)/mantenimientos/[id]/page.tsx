"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { useParams, useRouter } from "next/navigation";
import MaintenanceForm from "@/components/MaintenanceForm";
import { type Maintenance, getMaintenance, updateMaintenance } from "@/lib/maintenances";
import { MANAGER_ROLE, MECHANIC_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE];

export default function MaintenancePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [maintenance, setMaintenance] = useState<Maintenance | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getMaintenance(id).then((res) => {
      if (res.ok && res.data) setMaintenance(res.data.maintenance);
      else setLoadError(res.error ?? "No se pudo cargar el mantenimiento");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Mantenimiento</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{maintenance?.title ?? "Mantenimiento"}</h1>
      <p>
        <Link className="back-link" href="/mantenimientos">Volver a la lista</Link>
      </p>
      <div className="list-actions">
        <ExportButton path={`mantenimientos/${id}/`} label="Ver ficha en PDF" />
      </div>
      {loadError && <p role="alert">{loadError}</p>}
      {!maintenance && !loadError && <p>Cargando...</p>}

      {maintenance && maintenance.can_modify && (
        <MaintenanceForm
          maintenance={maintenance}
          onSubmit={(input) => updateMaintenance(id, input)}
          onSaved={() => router.push("/mantenimientos")}
          onCancel={() => router.push("/mantenimientos")}
        />
      )}

      {maintenance && !maintenance.can_modify && (
        <>
          <div className="table-scroll"><table>
            <tbody>
              <tr><th>Fecha</th><td>{maintenance.date}</td></tr>
              <tr><th>Tipo de servicio</th><td>{maintenance.service_type.label}</td></tr>
              <tr><th>Unidad</th><td>{maintenance.unit.label}</td></tr>
              <tr><th>Diagnóstico</th><td>{maintenance.diagnosis?.label ?? "Sin diagnóstico (preventivo)"}</td></tr>
              {maintenance.diagnosis && (
                <tr><th>Reparación terminada</th><td>{maintenance.repair_completed ? "Sí" : "No"}</td></tr>
              )}
              <tr><th>Km de servicio</th><td>{maintenance.service_mileage}</td></tr>
              <tr><th>Costo total</th><td>{maintenance.total_cost}</td></tr>
              <tr><th>Realizado por</th><td>{maintenance.operators.map((o) => o.label).join(", ")}</td></tr>
              {maintenance.diagnosis === null && (
                <tr><th>Plan preventivo</th><td>{maintenance.plan ? maintenance.plan.label : "Ninguno"}</td></tr>
              )}
              <tr><th>Refacciones</th><td>{maintenance.spare_parts.length ? maintenance.spare_parts.map((p) => `${p.label} × ${p.quantity}`).join(", ") : "Ninguna"}</td></tr>
              <tr><th>Observaciones</th><td style={{ whiteSpace: "pre-wrap" }}>{maintenance.observations || "Sin observaciones"}</td></tr>
            </tbody>
          </table></div>
          <p>Este mantenimiento no se puede modificar: solo los mecánicos que participaron en él pueden hacerlo.</p>
        </>
      )}
    </main>
  );
}
