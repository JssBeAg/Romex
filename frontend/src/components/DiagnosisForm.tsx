"use client";

import { FormEvent, useEffect, useState } from "react";
import { type ApiResult, validateOnServer } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import {
  type Diagnosis,
  type DiagnosisCatalogs,
  type DiagnosisInput,
  getDiagnosisCatalogs,
} from "@/lib/diagnoses";
import { today } from "@/lib/dates";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  fault_report_id: "Reporte de falla",
  date: "Fecha",
  detailed_cause: "Descripción del diagnóstico",
  requires_repair: "¿Requiere reparación?",
  unit_operable: "¿La unidad puede seguir operando?",
  severity_id: "Gravedad",
};

type Props = {
  diagnosis?: Diagnosis; // present when editing
  onSubmit: (input: DiagnosisInput) => Promise<ApiResult<{ diagnosis: Diagnosis }>>;
  onSaved: () => void;
  onCancel: () => void;
};


// A yes/no answer that starts empty so it has to be chosen
type YesNo = "" | "yes" | "no";
const toYesNo = (value: boolean | undefined): YesNo => (value === undefined ? "" : value ? "yes" : "no");
const fromYesNo = (value: YesNo): boolean | null => (value === "" ? null : value === "yes");

export default function DiagnosisForm({ diagnosis, onSubmit, onSaved, onCancel }: Props) {
  const editing = diagnosis !== undefined;

  const [reportId, setReportId] = useState(diagnosis ? String(diagnosis.fault_report.id) : "");
  const [date, setDate] = useState(diagnosis?.date ?? today());
  const [cause, setCause] = useState(diagnosis?.detailed_cause ?? "");
  const [requiresRepair, setRequiresRepair] = useState<YesNo>(toYesNo(diagnosis?.requires_repair));
  const [unitOperable, setUnitOperable] = useState<YesNo>(toYesNo(diagnosis?.unit_operable));
  const [severityId, setSeverityId] = useState(diagnosis ? String(diagnosis.severity.id) : "");

  const [catalogs, setCatalogs] = useState<DiagnosisCatalogs | null>(null);
  const [generalError, setGeneralError] = useState(""); // the catalogs could not be loaded
  const [submitting, setSubmitting] = useState(false);

  const input: DiagnosisInput = {
    fault_report_id: reportId ? Number(reportId) : null,
    date,
    detailed_cause: cause,
    requires_repair: fromYesNo(requiresRepair),
    unit_operable: fromYesNo(unitOperable),
    severity_id: severityId ? Number(severityId) : null,
  };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("diagnosticos", diagnosis?.id ?? null, current),
    labels: LABELS,
  });

  useEffect(() => {
    getDiagnosisCatalogs().then((res) => {
      if (res.ok && res.data) setCatalogs(res.data);
      else setGeneralError(res.error ?? "No se pudieron cargar los catálogos");
    });
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    setSubmitting(true);
    const res = await onSubmit(input);
    setSubmitting(false);

    if (res.ok) {
      onSaved();
      return;
    }
    feedback.rejectResult(res);
  }

  const fieldErrors = feedback.fieldErrors;
  const selectedReport = catalogs?.reports.find((r) => String(r.id) === reportId);

  function yesNo(name: string, value: YesNo, setValue: (v: YesNo) => void) {
    return (
      <>
        <label>
          <input type="radio" name={name} checked={value === "yes"} onChange={() => setValue("yes")} required /> Sí
        </label>{" "}
        <label>
          <input type="radio" name={name} checked={value === "no"} onChange={() => setValue("no")} required /> No
        </label>
        {fieldErrors(name)}
      </>
    );
  }

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      {generalError && <p role="alert">{generalError}</p>}

      <fieldset>
        <legend>Datos del diagnóstico</legend>

        {editing ? (
          <>
            <p>Reporte: {diagnosis.fault_report.label}</p>
            <p>
              <strong>Descripción del reporte</strong>
              <br />
              <span style={{ whiteSpace: "pre-wrap" }}>{diagnosis.fault_report.description}</span>
            </p>
          </>
        ) : (
          <p>
            <label htmlFor="fault_report_id">Reporte de falla (asignados a ti y sin diagnóstico)</label>
            <br />
            <select id="fault_report_id" value={reportId} onChange={(e) => setReportId(e.target.value)} required>
              <option value="">---------</option>
              {catalogs?.reports.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
            {catalogs && catalogs.reports.length === 0 && (
              <div className="hint">
                No tienes reportes asignados pendientes de diagnóstico. El gerente te los asigna.
              </div>
            )}
            {fieldErrors("fault_report_id")}
          </p>
        )}
        {!editing && selectedReport && (
          <p>
            <strong>Descripción del reporte</strong>
            <br />
            <span style={{ whiteSpace: "pre-wrap" }}>{selectedReport.description}</span>
          </p>
        )}

        <p>
          <label htmlFor="date">Fecha</label>
          <br />
          <input id="date" type="date" max={today()} value={date} onChange={(e) => setDate(e.target.value)} required />
          {fieldErrors("date")}
        </p>
        <p>
          <label htmlFor="detailed_cause">Descripción del diagnóstico (causa detallada)</label>
          <br />
          <textarea id="detailed_cause" rows={6} cols={60} value={cause} onChange={(e) => setCause(e.target.value)} required />
          {fieldErrors("detailed_cause")}
        </p>
        <p>
          ¿Requiere reparación?
          <br />
          {yesNo("requires_repair", requiresRepair, setRequiresRepair)}
        </p>
        <p>
          ¿La unidad puede seguir operando?
          <br />
          {yesNo("unit_operable", unitOperable, setUnitOperable)}
        </p>
        <p>
          <label htmlFor="severity_id">Gravedad</label>
          <br />
          <select id="severity_id" value={severityId} onChange={(e) => setSeverityId(e.target.value)} required>
            <option value="">---------</option>
            {catalogs?.severities.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          {fieldErrors("severity_id")}
        </p>
      </fieldset>

      <p>
        <button type="submit" disabled={submitting}>
          {submitting ? "Guardando..." : "Guardar"}
        </button>{" "}
        <button type="button" onClick={onCancel}>
          Cancelar
        </button>
      </p>

      {feedback.dialog}
    </form>
  );
}
