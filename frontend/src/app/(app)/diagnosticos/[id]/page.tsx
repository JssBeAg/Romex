"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { useParams, useRouter } from "next/navigation";
import DiagnosisForm from "@/components/DiagnosisForm";
import { type Diagnosis, getDiagnosis, updateDiagnosis } from "@/lib/diagnoses";
import { MANAGER_ROLE, MECHANIC_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE];

export default function DiagnosisPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getDiagnosis(id).then((res) => {
      if (res.ok && res.data) setDiagnosis(res.data.diagnosis);
      else setLoadError(res.error ?? "No se pudo cargar el diagnóstico");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Diagnóstico</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{diagnosis?.title ?? "Diagnóstico"}</h1>
      <p>
        <Link className="back-link" href="/diagnosticos">Volver a la lista</Link>
      </p>
      <div className="list-actions">
        <ExportButton path={`diagnosticos/${id}/`} label="Ver ficha en PDF" />
      </div>
      {loadError && <p role="alert">{loadError}</p>}
      {!diagnosis && !loadError && <p>Cargando...</p>}

      {diagnosis && diagnosis.can_modify && (
        <DiagnosisForm
          diagnosis={diagnosis}
          onSubmit={(input) => updateDiagnosis(id, input)}
          onSaved={() => router.push("/diagnosticos")}
          onCancel={() => router.push("/diagnosticos")}
        />
      )}

      {diagnosis && !diagnosis.can_modify && (
        <>
          <div className="table-scroll"><table>
            <tbody>
              <tr><th>Fecha</th><td>{diagnosis.date}</td></tr>
              <tr><th>Reporte</th><td>{diagnosis.fault_report.label}</td></tr>
              <tr><th>Descripción del reporte</th><td style={{ whiteSpace: "pre-wrap" }}>{diagnosis.fault_report.description}</td></tr>
              <tr><th>Unidad</th><td>{diagnosis.unit.label}</td></tr>
              <tr><th>Diagnosticó</th><td>{diagnosis.diagnosed_by.label}</td></tr>
              <tr><th>Descripción del diagnóstico (causa detallada)</th><td style={{ whiteSpace: "pre-wrap" }}>{diagnosis.detailed_cause}</td></tr>
              <tr><th>Requiere reparación</th><td>{diagnosis.requires_repair ? "Sí" : "No"}</td></tr>
              <tr><th>Unidad operable</th><td>{diagnosis.unit_operable ? "Sí" : "No"}</td></tr>
              <tr><th>Gravedad</th><td>{diagnosis.severity.label}</td></tr>
              <tr><th>Mantenimientos</th><td>{diagnosis.maintenances_count}</td></tr>
            </tbody>
          </table></div>
          <p>Este diagnóstico no se puede modificar: solo el mecánico que lo registró puede hacerlo.</p>
        </>
      )}
    </main>
  );
}
