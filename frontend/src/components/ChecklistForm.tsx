"use client";

import { FormEvent, useEffect, useState } from "react";
import { type ApiResult, type Option, validateOnServer } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import {
  type Checklist,
  type ChecklistInput,
  getChecklistCatalogs,
} from "@/lib/checklists";
import { today } from "@/lib/dates";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  unit_id: "Unidad",
  date: "Fecha",
  recorded_mileage: "Kilometraje registrado",
  tire_pressure: "Presión de llantas",
  tire_tread_depth: "Profundidad de llantas",
  lights_ok: "¿Las luces funcionan correctamente?",
  fluids_ok: "¿Los niveles de fluidos son correctos?",
  no_cracks: "¿La unidad está libre de grietas?",
  trip_description: "Descripción del viaje",
};

type Props = {
  checklist?: Checklist; // present when editing
  onSubmit: (input: ChecklistInput) => Promise<ApiResult<{ checklist: Checklist }>>;
  onSaved: () => void;
  onCancel: () => void;
};

type CheckField = "lights_ok" | "fluids_ok" | "no_cracks";

const CHECKS: { name: CheckField; label: string }[] = [
  { name: "lights_ok", label: "¿Las luces funcionan correctamente?" },
  { name: "fluids_ok", label: "¿Los niveles de fluidos son correctos?" },
  { name: "no_cracks", label: "¿La unidad está libre de grietas?" },
];

export default function ChecklistForm({ checklist, onSubmit, onSaved, onCancel }: Props) {
  const [unitId, setUnitId] = useState(checklist ? String(checklist.unit.id) : "");
  const [date, setDate] = useState(checklist?.date ?? today());
  const [mileage, setMileage] = useState(checklist ? String(checklist.recorded_mileage) : "");
  const [pressure, setPressure] = useState(checklist?.tire_pressure ?? "");
  const [tread, setTread] = useState(checklist?.tire_tread_depth ?? "");
  // No default answers: each check must be chosen explicitly
  const [checks, setChecks] = useState<Record<CheckField, boolean | null>>({
    lights_ok: checklist?.lights_ok ?? null,
    fluids_ok: checklist?.fluids_ok ?? null,
    no_cracks: checklist?.no_cracks ?? null,
  });
  const [description, setDescription] = useState(checklist?.trip_description ?? "");

  const [loadedUnits, setLoadedUnits] = useState<Option[] | null>(null);
  const [notOperable, setNotOperable] = useState<Option[]>([]); // assigned units left out: not fit to operate
  const [generalError, setGeneralError] = useState(""); // the catalogs could not be loaded
  const [submitting, setSubmitting] = useState(false);

  // The operator's assigned units, plus the one this checklist already has (it may no longer be theirs)
  const units = [...(loadedUnits ?? [])];
  if (checklist && loadedUnits && !units.some((option) => option.id === checklist.unit.id)) {
    units.unshift(checklist.unit);
  }
  const noUnits = !checklist && loadedUnits !== null && units.length === 0;

  const input: ChecklistInput = {
    unit_id: unitId ? Number(unitId) : null,
    date,
    recorded_mileage: mileage,
    tire_pressure: pressure,
    tire_tread_depth: tread,
    ...checks,
    trip_description: description,
  };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("checklists", checklist?.id ?? null, current),
    labels: LABELS,
  });

  useEffect(() => {
    getChecklistCatalogs().then((res) => {
      if (res.ok && res.data) {
        setLoadedUnits(res.data.units);
        setNotOperable(res.data.not_operable);
      }
      else setGeneralError(res.error ?? "No se pudieron cargar las unidades");
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

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      {generalError && <p role="alert">{generalError}</p>}

      <fieldset>
        <legend>Datos del checklist</legend>
        <p>
          <label htmlFor="unit_id">Unidad</label>
          <br />
          <select id="unit_id" value={unitId} onChange={(e) => setUnitId(e.target.value)} required>
            <option value="">---------</option>
            {units.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          {noUnits && notOperable.length === 0 && (
            <div className="hint">No tienes unidades asignadas. Pide al gerente que te asigne una.</div>
          )}
          {noUnits && notOperable.length > 0 && (
            <div className="hint">No tienes unidades aptas para operar ahora.</div>
          )}
          {!checklist && notOperable.length > 0 && (
            <div className="hint">
              No aparecen por no estar aptas para operar (tienen una falla diagnosticada sin reparar):{" "}
              {notOperable.map((option) => option.label).join(", ")}.
            </div>
          )}
          {fieldErrors("unit_id")}
        </p>
        <p>
          <label htmlFor="date">Fecha</label>
          <br />
          <input id="date" type="date" max={today()} value={date} onChange={(e) => setDate(e.target.value)} required />
          {fieldErrors("date")}
        </p>
        <p>
          <label htmlFor="recorded_mileage">Kilometraje registrado (km)</label>
          <br />
          <input
            id="recorded_mileage"
            type="number"
            min={0}
            step={1}
            value={mileage}
            onChange={(e) => setMileage(e.target.value)}
            required
          />
          {fieldErrors("recorded_mileage")}
        </p>
        <p>
          <label htmlFor="tire_pressure">Presión de llantas (PSI)</label>
          <br />
          <input
            id="tire_pressure"
            type="number"
            min={0}
            step={0.1}
            value={pressure}
            onChange={(e) => setPressure(e.target.value)}
            required
          />
          {fieldErrors("tire_pressure")}
        </p>
        <p>
          <label htmlFor="tire_tread_depth">Profundidad de llantas (mm)</label>
          <br />
          <input
            id="tire_tread_depth"
            type="number"
            min={0}
            step={0.1}
            value={tread}
            onChange={(e) => setTread(e.target.value)}
            required
          />
          {fieldErrors("tire_tread_depth")}
        </p>
      </fieldset>

      <fieldset>
        <legend>Revisión</legend>
        {CHECKS.map(({ name, label }) => (
          <div key={name} role="radiogroup" aria-label={label} style={{ marginBottom: "0.75rem" }}>
            <div>{label}</div>
            <label>
              <input
                type="radio"
                name={name}
                checked={checks[name] === true}
                onChange={() => setChecks((previous) => ({ ...previous, [name]: true }))}
                required
              />{" "}
              Sí
            </label>{" "}
            <label>
              <input
                type="radio"
                name={name}
                checked={checks[name] === false}
                onChange={() => setChecks((previous) => ({ ...previous, [name]: false }))}
                required
              />{" "}
              No
            </label>
            {fieldErrors(name)}
          </div>
        ))}
        <p>
          <label htmlFor="trip_description">Descripción del viaje</label>
          <br />
          <textarea
            id="trip_description"
            rows={5}
            cols={60}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
          {fieldErrors("trip_description")}
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
