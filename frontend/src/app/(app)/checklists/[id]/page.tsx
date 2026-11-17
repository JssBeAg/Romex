"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { useParams, useRouter } from "next/navigation";
import ChecklistForm from "@/components/ChecklistForm";
import { MANAGER_ROLE, OPERATOR_ROLE } from "@/lib/roles";
import { type Checklist, getChecklist, updateChecklist, yesNo } from "@/lib/checklists";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, OPERATOR_ROLE];

export default function ChecklistPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getChecklist(id).then((res) => {
      if (res.ok && res.data) setChecklist(res.data.checklist);
      else setLoadError(res.error ?? "No se pudo cargar el checklist");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Checklist</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{checklist?.title ?? "Checklist"}</h1>
      <p>
        <Link className="back-link" href="/checklists">Volver a la lista</Link>
      </p>
      <div className="list-actions">
        <ExportButton path={`checklists/${id}/`} label="Ver ficha en PDF" />
      </div>
      {loadError && <p role="alert">{loadError}</p>}
      {!checklist && !loadError && <p>Cargando...</p>}

      {checklist && checklist.can_modify && (
        <ChecklistForm
          checklist={checklist}
          onSubmit={(input) => updateChecklist(id, input)}
          onSaved={() => router.push("/checklists")}
          onCancel={() => router.push("/checklists")}
        />
      )}

      {checklist && !checklist.can_modify && (
        <div className="table-scroll"><table>
          <tbody>
            <tr><th>Folio</th><td>{checklist.folio}</td></tr>
            <tr><th>Fecha</th><td>{checklist.date}</td></tr>
            <tr><th>Unidad</th><td>{checklist.unit.label}</td></tr>
            <tr><th>Registró</th><td>{checklist.completed_by.label}</td></tr>
            <tr><th>Kilometraje registrado</th><td>{checklist.recorded_mileage} km</td></tr>
            <tr><th>Presión de llantas</th><td>{checklist.tire_pressure} PSI</td></tr>
            <tr><th>Profundidad de llantas</th><td>{checklist.tire_tread_depth} mm</td></tr>
            <tr><th>Luces</th><td>{yesNo(checklist.lights_ok)}</td></tr>
            <tr><th>Fluidos</th><td>{yesNo(checklist.fluids_ok)}</td></tr>
            <tr><th>Sin grietas</th><td>{yesNo(checklist.no_cracks)}</td></tr>
            <tr><th>Descripción del viaje</th><td style={{ whiteSpace: "pre-wrap" }}>{checklist.trip_description}</td></tr>
          </tbody>
        </table></div>
      )}
    </main>
  );
}
