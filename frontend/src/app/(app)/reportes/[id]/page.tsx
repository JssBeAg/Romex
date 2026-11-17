"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { useParams, useRouter } from "next/navigation";
import EvidenceImage from "@/components/EvidenceImage";
import ReportForm from "@/components/ReportForm";
import ReportMechanics from "@/components/ReportMechanics";
import StatusHistory from "@/components/StatusHistory";
import { MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE } from "@/lib/roles";
import { type Report, getReport, updateReport } from "@/lib/reports";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE];

export default function ReportPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [report, setReport] = useState<Report | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getReport(id).then((res) => {
      if (res.ok && res.data) setReport(res.data.report);
      else setLoadError(res.error ?? "No se pudo cargar el reporte");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Reporte de falla</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{report?.title ?? "Reporte de falla"}</h1>
      <p>
        <Link className="back-link" href="/reportes">Volver a la lista</Link>
      </p>
      <div className="list-actions">
        <ExportButton path={`reportes-fallas/${id}/`} label="Ver ficha en PDF" />
      </div>
      {loadError && <p role="alert">{loadError}</p>}
      {!report && !loadError && <p>Cargando...</p>}

      {report && report.can_modify && (
        <ReportForm
          report={report}
          onSubmit={(input) => updateReport(id, input)}
          onSaved={() => router.push("/reportes")}
          onCancel={() => router.push("/reportes")}
        />
      )}

      {report && !report.can_modify && (
        <>
          <div className="table-scroll"><table>
            <tbody>
              <tr><th>Fecha</th><td>{report.date}</td></tr>
              <tr><th>Unidad</th><td>{report.unit.label}</td></tr>
              <tr><th>Ubicación</th><td>{report.location}</td></tr>
              <tr><th>Estatus</th><td>{report.status.label}</td></tr>
              <tr><th>Reportó</th><td>{report.reported_by.label}</td></tr>
              <tr>
                <th>Evidencia</th>
                <td>
                  {report.evidence.length > 0 ? (
                    <div className="thumb-grid">
                      {report.evidence.map((photo) => (
                        <EvidenceImage key={photo.id} path={photo.url} name={photo.name} />
                      ))}
                    </div>
                  ) : (
                    "Sin evidencia"
                  )}
                </td>
              </tr>
              <tr><th>Descripción</th><td style={{ whiteSpace: "pre-wrap" }}>{report.description}</td></tr>
              <tr><th>Diagnóstico</th><td>{report.has_diagnosis ? "Ya tiene diagnóstico" : "Sin diagnóstico"}</td></tr>
            </tbody>
          </table></div>
          <p>
            Este reporte no se puede modificar: solo el operador que lo creó puede hacerlo, y solo mientras esté pendiente.
          </p>
        </>
      )}

      {report && report.mechanics && <ReportMechanics report={report} onChange={setReport} />}

      {report && report.status_history.length > 0 && <StatusHistory history={report.status_history} />}
    </main>
  );
}
