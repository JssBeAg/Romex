"use client";

import { FormEvent, useEffect, useState } from "react";
import { type ApiResult, type Option, validateOnServer } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import { type Plan, type PlanInput, getPlanCatalogs } from "@/lib/preventive";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  name: "Nombre",
  description: "Descripción",
  every_km: "Cada (km)",
  every_days: "Cada (días)",
  unit_model_id: "Aplica a",
  is_active: "Activo",
};

type Props = {
  plan?: Plan; // present when editing
  onSubmit: (input: PlanInput) => Promise<ApiResult<{ plan: Plan }>>;
  onSaved: () => void;
  onCancel: () => void;
};

export default function PlanForm({ plan, onSubmit, onSaved, onCancel }: Props) {
  const [name, setName] = useState(plan?.name ?? "");
  const [description, setDescription] = useState(plan?.description ?? "");
  const [everyKm, setEveryKm] = useState(plan?.every_km ? String(plan.every_km) : "");
  const [everyDays, setEveryDays] = useState(plan?.every_days ? String(plan.every_days) : "");
  const [modelId, setModelId] = useState(plan?.unit_model ? String(plan.unit_model.id) : "");
  const [isActive, setIsActive] = useState(plan?.is_active ?? true);
  const [models, setModels] = useState<Option[]>([]);
  const [generalError, setGeneralError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const input: PlanInput = {
    name,
    description,
    every_km: everyKm,
    every_days: everyDays,
    unit_model_id: modelId ? Number(modelId) : null,
    is_active: isActive,
  };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("preventivo/planes", plan?.id ?? null, current),
    labels: LABELS,
  });
  const fieldErrors = feedback.fieldErrors;

  useEffect(() => {
    getPlanCatalogs().then((res) => {
      if (res.ok && res.data) setModels(res.data.models);
      else setGeneralError(res.error ?? "No se pudieron cargar los modelos");
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

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      {generalError && <p role="alert">{generalError}</p>}
      <fieldset>
        <legend>Datos del plan</legend>
        <p>
          <label htmlFor="name">Nombre</label>
          <br />
          <input id="name" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} required />
          {fieldErrors("name")}
        </p>
        <p>
          <label htmlFor="description">Descripción (opcional)</label>
          <br />
          <textarea id="description" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          {fieldErrors("description")}
        </p>
        <p>
          <label htmlFor="every_km">Se repite cada (km)</label>
          <br />
          <input id="every_km" type="number" min={1} step={1} value={everyKm} onChange={(e) => setEveryKm(e.target.value)} />
          {fieldErrors("every_km")}
        </p>
        <p>
          <label htmlFor="every_days">Se repite cada (días)</label>
          <br />
          <input id="every_days" type="number" min={1} step={1} value={everyDays} onChange={(e) => setEveryDays(e.target.value)} />
          <span className="hint"> Llena uno o ambos: vence lo que ocurra primero.</span>
          {fieldErrors("every_days")}
        </p>
        <p>
          <label htmlFor="unit_model_id">Aplica a</label>
          <br />
          <select id="unit_model_id" value={modelId} onChange={(e) => setModelId(e.target.value)}>
            <option value="">Todas las unidades</option>
            {models.map((option) => (
              <option key={option.id} value={option.id}>
                Solo {option.label}
              </option>
            ))}
          </select>
          {fieldErrors("unit_model_id")}
        </p>
        <p>
          <label>
            <input type="checkbox" data-field="is_active" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Activo
          </label>
          <span className="hint"> Un plan inactivo deja de dar alertas, pero conserva su historial.</span>
          {fieldErrors("is_active")}
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
