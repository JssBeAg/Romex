"use client";

import { FormEvent, useEffect, useState } from "react";
import { type ApiResult, validateOnServer } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import {
  type Maintenance,
  type MaintenanceCatalogs,
  type MaintenanceInput,
  getMaintenanceCatalogs,
} from "@/lib/maintenances";
import { today } from "@/lib/dates";

const CORRECTIVE = "Correctivo";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  service_type_id: "Tipo de servicio",
  diagnosis_id: "Diagnóstico",
  unit_id: "Unidad",
  service_mileage: "Kilometraje del servicio",
  total_cost: "Costo total",
  date: "Fecha",
  repair_completed: "La reparación quedó terminada",
  observations: "Observaciones",
  operator_ids: "Quién lo realizó",
  spare_parts: "Refacciones usadas",
  plan_id: "Plan preventivo",
};

type Props = {
  maintenance?: Maintenance; // present when editing
  onSubmit: (input: MaintenanceInput) => Promise<ApiResult<{ maintenance: Maintenance }>>;
  onSaved: () => void;
  onCancel: () => void;
};


export default function MaintenanceForm({ maintenance, onSubmit, onSaved, onCancel }: Props) {
  const editing = maintenance !== undefined;

  const [serviceTypeId, setServiceTypeId] = useState("");
  const [diagnosisId, setDiagnosisId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [planId, setPlanId] = useState(maintenance?.plan ? String(maintenance.plan.id) : "");
  const [mileage, setMileage] = useState(maintenance ? String(maintenance.service_mileage) : "");
  const [cost, setCost] = useState(maintenance?.total_cost ?? "");
  const [date, setDate] = useState(maintenance?.date ?? today());
  const [observations, setObservations] = useState(maintenance?.observations ?? "");
  const [repairCompleted, setRepairCompleted] = useState(maintenance?.repair_completed ?? false);
  const [operatorIds, setOperatorIds] = useState<number[]>(maintenance?.operators.map((o) => o.id) ?? []);
  // Parts used: part id -> pieces (as typed)
  const [parts, setParts] = useState<Record<number, string>>(
    Object.fromEntries((maintenance?.spare_parts ?? []).map((p) => [p.id, String(p.quantity)]))
  );

  const [catalogs, setCatalogs] = useState<MaintenanceCatalogs | null>(null);
  const [generalError, setGeneralError] = useState(""); // the catalogs could not be loaded
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getMaintenanceCatalogs().then((res) => {
      if (res.ok && res.data) {
        setCatalogs(res.data);
        // The mechanic who registers it is always one of the operators
        const me = res.data.current_user_id;
        setOperatorIds((previous) => (previous.includes(me) ? previous : [...previous, me]));
      } else {
        setGeneralError(res.error ?? "No se pudieron cargar los catálogos");
      }
    });
  }, []);

  const selectedType = catalogs?.service_types.find((t) => String(t.id) === serviceTypeId);
  const isCorrective = selectedType?.label === CORRECTIVE;
  // The "repair finished" check only exists for corrective maintenance (the ones with a diagnosis)
  const canCompleteRepair = editing ? maintenance.diagnosis !== null : isCorrective;

  // Preventive service: the plan it fulfils can be chosen (only plans that apply to the unit's model)
  const isPreventive = editing ? maintenance.diagnosis === null : selectedType !== undefined && !isCorrective;
  const selectedDiagnosis = catalogs?.diagnoses.find((d) => String(d.id) === diagnosisId);
  const unitIdForPlan = editing ? maintenance.unit.id : unitId ? Number(unitId) : null;
  const unitModelId = catalogs?.units.find((u) => u.id === unitIdForPlan)?.unit_model_id;
  const planOptions = (catalogs?.plans ?? []).filter(
    (p) => (p.unit_model_id === null || p.unit_model_id === unitModelId) || String(p.id) === planId
  );

  // What the form sends. The server also checks it while it is being filled in.
  const input: MaintenanceInput = {
    service_type_id: serviceTypeId ? Number(serviceTypeId) : null,
    diagnosis_id: isCorrective && diagnosisId ? Number(diagnosisId) : null,
    unit_id: selectedType && !isCorrective && unitId ? Number(unitId) : null,
    service_mileage: mileage,
    total_cost: cost,
    date,
    observations,
    repair_completed: canCompleteRepair && repairCompleted,
    plan_id: isPreventive && planId ? Number(planId) : null,
    operator_ids: operatorIds,
    spare_parts: Object.entries(parts).map(([id, quantity]) => ({ id: Number(id), quantity })),
  };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("mantenimientos", maintenance?.id ?? null, current),
    labels: LABELS,
  });

  // Parts that can be chosen: the ones in stock, and the ones this maintenance already uses
  // (when editing, its own pieces count as available again)
  const partOptions = (catalogs?.spare_parts ?? []).map((option) => {
    const own = maintenance?.spare_parts.find((p) => p.id === option.id)?.quantity ?? 0;
    return { option, available: Math.max(option.stock + own, 0) };
  });
  const inStock = partOptions.filter(({ option, available }) => available > 0 || option.id in parts);
  const outOfStock = partOptions.length - inStock.length;

  function togglePart(id: number) {
    setParts((previous) => {
      const next = { ...previous };
      if (id in next) delete next[id];
      else next[id] = "1";
      return next;
    });
  }

  function toggle(list: number[], setList: (v: number[]) => void, id: number) {
    setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  }

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

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      {generalError && <p role="alert">{generalError}</p>}

      <fieldset>
        <legend>Servicio</legend>

        {editing ? (
          <>
            <p>Tipo de servicio: {maintenance.service_type.label}</p>
            <p>Unidad: {maintenance.unit.label}</p>
            {maintenance.diagnosis && (
              <>
                <p>Diagnóstico: {maintenance.diagnosis.label}</p>
                <p>
                  <strong>Descripción del diagnóstico</strong>
                  <br />
                  <span style={{ whiteSpace: "pre-wrap" }}>{maintenance.diagnosis.detailed_cause}</span>
                </p>
              </>
            )}
          </>
        ) : (
          <>
            <p>
              <label htmlFor="service_type_id">Tipo de servicio</label>
              <br />
              <select id="service_type_id" value={serviceTypeId} onChange={(e) => setServiceTypeId(e.target.value)} required>
                <option value="">---------</option>
                {catalogs?.service_types.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
              {fieldErrors("service_type_id")}
            </p>
            {selectedType && isCorrective && (
              <p>
                <label htmlFor="diagnosis_id">Diagnóstico (tus diagnósticos que requieren reparación)</label>
                <br />
                <select id="diagnosis_id" value={diagnosisId} onChange={(e) => setDiagnosisId(e.target.value)} required>
                  <option value="">---------</option>
                  {catalogs?.diagnoses.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {fieldErrors("diagnosis_id")}
              </p>
            )}
            {selectedType && isCorrective && selectedDiagnosis && (
              <p>
                <strong>Descripción del diagnóstico</strong>
                <br />
                <span style={{ whiteSpace: "pre-wrap" }}>{selectedDiagnosis.detailed_cause}</span>
              </p>
            )}
            {selectedType && !isCorrective && (
              <p>
                <label htmlFor="unit_id">Unidad</label>
                <br />
                <select id="unit_id" value={unitId} onChange={(e) => setUnitId(e.target.value)} required>
                  <option value="">---------</option>
                  {catalogs?.units.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {fieldErrors("unit_id")}
                {fieldErrors("diagnosis_id")}
              </p>
            )}
          </>
        )}

        {isPreventive && unitIdForPlan !== null && (
          <p>
            <label htmlFor="plan_id">Plan preventivo que cumple (opcional)</label>
            <br />
            <select id="plan_id" value={planId} onChange={(e) => setPlanId(e.target.value)}>
              <option value="">Ninguno (servicio preventivo sin plan)</option>
              {planOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
            <span className="hint"> Al elegirlo, se reinicia el conteo de km y días de ese plan para la unidad.</span>
            {fieldErrors("plan_id")}
          </p>
        )}
        <p>
          <label htmlFor="service_mileage">Kilometraje del servicio</label>
          <br />
          <input id="service_mileage" type="number" min={0} step={1} value={mileage} onChange={(e) => setMileage(e.target.value)} required />
          {fieldErrors("service_mileage")}
        </p>
        <p>
          <label htmlFor="total_cost">Costo total</label>
          <br />
          <input id="total_cost" type="number" min={0} step="0.01" value={cost} onChange={(e) => setCost(e.target.value)} required />
          {fieldErrors("total_cost")}
        </p>
        <p>
          <label htmlFor="date">Fecha</label>
          <br />
          <input id="date" type="date" max={today()} value={date} onChange={(e) => setDate(e.target.value)} required />
          {fieldErrors("date")}
        </p>
        {canCompleteRepair && (
          <p>
            <label>
              <input
                type="checkbox"
                data-field="repair_completed"
                checked={repairCompleted}
                onChange={(e) => setRepairCompleted(e.target.checked)}
              />{" "}
              La reparación quedó terminada
            </label>
            <br />
            <span className="hint">Al marcarla, el reporte de falla pasa a «Reparado».</span>
            {fieldErrors("repair_completed")}
          </p>
        )}
        <p>
          <label htmlFor="observations">Observaciones (opcional)</label>
          <br />
          <textarea id="observations" rows={5} cols={60} value={observations} onChange={(e) => setObservations(e.target.value)} />
          {fieldErrors("observations")}
        </p>
      </fieldset>

      <fieldset>
        <legend>Quién lo realizó</legend>
        {catalogs?.operators.map((option) => {
          const isMe = option.id === catalogs.current_user_id;
          return (
            <div key={option.id}>
              <label>
                <input
                  type="checkbox"
                  data-field="operator_ids"
                  checked={operatorIds.includes(option.id)}
                  disabled={isMe}
                  onChange={() => toggle(operatorIds, setOperatorIds, option.id)}
                />{" "}
                {option.label}
                {isMe ? " (tú, siempre incluido)" : ""}
              </label>
            </div>
          );
        })}
        {fieldErrors("operator_ids")}
      </fieldset>

      <fieldset>
        <legend>Refacciones usadas (opcional)</legend>
        <div className="span-all">
          <p className="hint">Las piezas que uses se descuentan de las existencias.</p>
          {catalogs && catalogs.spare_parts.length === 0 && <p>No hay refacciones registradas.</p>}
          {catalogs && catalogs.spare_parts.length > 0 && inStock.length === 0 && (
            <p>No hay refacciones con existencias. El gerente debe registrar una entrada.</p>
          )}
          {inStock.map(({ option, available }) => {
            const selected = option.id in parts;
            return (
              <div key={option.id} className="assign-row">
                <label>
                  <input
                    type="checkbox"
                    data-field="spare_parts"
                    checked={selected}
                    onChange={() => togglePart(option.id)}
                  />{" "}
                  {option.label}
                </label>
                <span className="hint">Disponibles: {available}</span>
                {selected && (
                  <>
                    <label htmlFor={`part_${option.id}`}>Cantidad</label>
                    <input
                      id={`part_${option.id}`}
                      data-field="spare_parts"
                      type="number"
                      min={1}
                      max={available}
                      step={1}
                      value={parts[option.id]}
                      onChange={(e) => setParts((previous) => ({ ...previous, [option.id]: e.target.value }))}
                    />
                  </>
                )}
              </div>
            );
          })}
          {outOfStock > 0 && (
            <p className="hint">
              {outOfStock} {outOfStock === 1 ? "refacción sin existencias no se muestra" : "refacciones sin existencias no se muestran"}.
            </p>
          )}
        </div>
        {fieldErrors("spare_parts")}
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
