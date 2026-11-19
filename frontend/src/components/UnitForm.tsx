"use client";

import { useStates } from "@/lib/locations";
import { FormEvent, useEffect, useState } from "react";
import { type ApiResult, validateOnServer } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import { type Unit, type UnitCatalogs, type UnitInput, getUnitCatalogs } from "@/lib/units";
import { today } from "@/lib/dates";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  economic_number: "Número económico",
  unit_model_id: "Modelo",
  mileage: "Kilometraje",
  is_active: "Activa",
  plate_state: "Estado de la placa",
  plate_identifier: "Placa",
  plate_start_date: "Vigente desde",
  plate: "Placa",
  operator: "Operador",
};

type Props = {
  unit?: Unit; // present when editing
  onSubmit: (input: UnitInput) => Promise<ApiResult<{ unit: Unit }>>;
  onSaved: () => void;
  onCancel: () => void;
};


export default function UnitForm({ unit, onSubmit, onSaved, onCancel }: Props) {
  const editing = unit !== undefined;

  const [economicNumber, setEconomicNumber] = useState(unit?.economic_number ?? "");
  const [brandId, setBrandId] = useState(unit ? String(unit.brand.id) : "");
  const [modelId, setModelId] = useState(unit ? String(unit.unit_model.id) : "");
  const [mileage, setMileage] = useState(unit ? String(unit.mileage) : "");
  const [isActive, setIsActive] = useState(unit?.is_active ?? true);
  // The plate fields: required to create; when editing they replace the current plate
  const [plateStateId, setPlateStateId] = useState("");
  const [plateIdentifier, setPlateIdentifier] = useState("");
  const [plateStart, setPlateStart] = useState(today());

  // Change of operator, applied when the form is saved. With a current operator the manager
  // either changes it (ends it and opens the new one the same day) or removes it (ends it).
  const current = unit?.current_operator ?? null;
  const [operatorMode, setOperatorMode] = useState<"keep" | "change" | "remove">("keep");
  const [newOperatorId, setNewOperatorId] = useState("");
  const [operatorDate, setOperatorDate] = useState(today()); // end of the current one and/or start of the new one

  const { states: stateNames, error: statesError } = useStates();
  const [catalogs, setCatalogs] = useState<UnitCatalogs | null>(null);
  const [generalError, setGeneralError] = useState(""); // the catalogs could not be loaded
  const [submitting, setSubmitting] = useState(false);

  // When editing, the plate is only sent if something was typed in the new-plate section
  const plateTouched = plateIdentifier.trim() !== "" || plateStateId !== "";
  const input: UnitInput = {
    economic_number: economicNumber,
    unit_model_id: modelId ? Number(modelId) : null,
    mileage,
    is_active: isActive,
    plate:
      !editing || plateTouched
        ? {
            state: plateStateId,
            identifier: plateIdentifier,
            start_date: plateStart,
          }
        : null,
    end_operator:
      current && operatorMode !== "keep" ? { assignment_id: current.id, end_date: operatorDate } : null,
    new_operator:
      newOperatorId && (!current || operatorMode === "change")
        ? { operator_id: Number(newOperatorId), start_date: operatorDate }
        : null,
  };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("unidades", unit?.id ?? null, current),
    labels: LABELS,
  });

  useEffect(() => {
    getUnitCatalogs(unit?.id).then((res) => {
      if (res.ok && res.data) setCatalogs(res.data);
      else setGeneralError(res.error ?? "No se pudieron cargar los catálogos");
    });
  }, [unit?.id]);

  const modelsOfBrand = catalogs?.models.filter((m) => String(m.brand_id) === brandId) ?? [];

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

  function chooseOperatorMode(mode: "keep" | "change" | "remove") {
    setOperatorMode(mode);
    setNewOperatorId("");
    setOperatorDate(today());
    feedback.touch("operator");
  }

  // The selector offers the operators without a unit; the current one is shown but cannot be chosen
  const operatorOptions = catalogs?.operators ?? [];
  const operatorSelect = (
    <label>
      {current ? "Nuevo operador" : "Operador"}{" "}
      <select
        id="new_operator"
        data-field="operator"
        value={newOperatorId}
        onChange={(e) => {
          setNewOperatorId(e.target.value);
          feedback.touch("operator");
        }}
      >
        <option value="">{current ? "Elige un operador" : "Sin operador"}</option>
        {operatorOptions.map((option) => (
          <option key={option.id} value={option.id} disabled={option.current}>
            {option.current ? `${option.label} (actual)` : option.label}
          </option>
        ))}
      </select>
    </label>
  );
  const operatorDateInput = (label: string) => (
    <label>
      {label}{" "}
      <input
        id="operator_date"
        type="date"
        data-field="operator"
        min={current?.start_date}
        max={today()}
        value={operatorDate}
        onChange={(e) => setOperatorDate(e.target.value)}
      />
    </label>
  );

  const operatorsSection = (
    <fieldset>
      <legend>Operador</legend>
      <div className="span-all">
        <p className="hint">
          Una unidad tiene un solo operador a la vez, y un operador una sola unidad. Solo ese operador
          puede reportar fallas y llenar checklists de la unidad. Los cambios se aplican al guardar.
        </p>

        {current ? (
          <p>
            Operador actual: <strong>{current.operator.label}</strong>, desde {current.start_date}.
          </p>
        ) : (
          editing && <p>La unidad no tiene operador.</p>
        )}

        {current && operatorMode === "keep" && (
          <div className="assign-row">
            <button type="button" onClick={() => chooseOperatorMode("change")}>
              Cambiar de operador
            </button>
            <button type="button" onClick={() => chooseOperatorMode("remove")}>
              Quitar operador
            </button>
          </div>
        )}

        {current && operatorMode === "change" && (
          <div className="assign-row">
            {operatorSelect}
            {operatorDateInput("A partir de")}
            <button type="button" onClick={() => chooseOperatorMode("keep")}>
              Cancelar cambio
            </button>
          </div>
        )}
        {current && operatorMode === "change" && (
          <p className="hint">
            {current.operator.label} dejará la unidad en esa fecha y el nuevo operador la tendrá desde ese día.
          </p>
        )}

        {current && operatorMode === "remove" && (
          <div className="assign-row">
            {operatorDateInput(`${current.operator.label} deja la unidad el`)}
            <button type="button" onClick={() => chooseOperatorMode("keep")}>
              No quitar
            </button>
          </div>
        )}

        {!current && (
          <div className="assign-row">
            {operatorSelect}
            {operatorDateInput("Desde")}
          </div>
        )}
        {fieldErrors("operator")}

        {editing && (
          <>
            <h3>Historial de operadores</h3>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Operador</th>
                    <th>Desde</th>
                    <th>Hasta</th>
                  </tr>
                </thead>
                <tbody>
                  {unit.operators.length === 0 && (
                    <tr>
                      <td colSpan={3}>La unidad no ha tenido operadores.</td>
                    </tr>
                  )}
                  {unit.operators.map((assignment) => (
                    <tr key={assignment.id}>
                      <td>{assignment.operator.label}</td>
                      <td>{assignment.start_date}</td>
                      <td>{assignment.end_date ?? "Actual"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </fieldset>
  );

  const plateFields = (
    <>
      <p>
        <label htmlFor="plate_state">Estado de la placa</label>
        <br />
        <select
          id="plate_state"
          data-field="plate_state"
          value={plateStateId}
          onChange={(e) => setPlateStateId(e.target.value)}
          required={!editing}
        >
          <option value="">---------</option>
          {stateNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        {statesError && <span className="field-error">{statesError}</span>}
        {fieldErrors("plate_state")}
      </p>
      <p>
        <label htmlFor="plate_identifier">Placa</label>
        <br />
        <input
          id="plate_identifier"
          value={plateIdentifier}
          maxLength={15}
          onChange={(e) => setPlateIdentifier(e.target.value)}
          required={!editing}
        />
        {fieldErrors("plate_identifier")}
      </p>
      <p>
        <label htmlFor="plate_start_date">Vigente desde</label>
        <br />
        <input
          id="plate_start_date"
          type="date"
          value={plateStart}
          onChange={(e) => setPlateStart(e.target.value)}
          required
        />
        {fieldErrors("plate_start_date")}
      </p>
      {fieldErrors("plate")}
    </>
  );

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      {generalError && <p role="alert">{generalError}</p>}

      <fieldset>
        <legend>Datos de la unidad</legend>
        <p>
          <label htmlFor="economic_number">Número económico</label>
          <br />
          <input id="economic_number" value={economicNumber} onChange={(e) => setEconomicNumber(e.target.value)} maxLength={20} required />
          {fieldErrors("economic_number")}
        </p>
        <p>
          <label htmlFor="brand_id">Marca</label>
          <br />
          <select
            id="brand_id"
            value={brandId}
            onChange={(e) => {
              setBrandId(e.target.value);
              setModelId("");
            }}
            required
          >
            <option value="">---------</option>
            {catalogs?.brands.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="unit_model_id">Modelo</label>
          <br />
          <select id="unit_model_id" value={modelId} onChange={(e) => setModelId(e.target.value)} required>
            <option value="">---------</option>
            {modelsOfBrand.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          {fieldErrors("unit_model_id")}
        </p>
        <p>
          <label htmlFor="mileage">Kilometraje</label>
          <br />
          <input id="mileage" type="number" min={0} step={1} value={mileage} onChange={(e) => setMileage(e.target.value)} required />
          {fieldErrors("mileage")}
        </p>
        <p>
          <label>
            <input id="is_active" type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Activa
          </label>
          <span className="hint"> Una unidad inactiva conserva su historial, pero ya no recibe reportes, revisiones, mantenimientos ni operadores.</span>
          {fieldErrors("is_active")}
        </p>
      </fieldset>

      {editing ? (
        <>
          <fieldset>
            <legend>Placa actual</legend>
            {unit.current_plate ? (
              <p>
                {unit.current_plate.identifier} ({unit.current_plate.state}), vigente desde{" "}
                {unit.current_plate.start_date}
              </p>
            ) : (
              <p>La unidad no tiene una placa vigente.</p>
            )}
          </fieldset>

          <fieldset>
            <legend>Asignar una placa nueva (opcional)</legend>
            <p>La placa actual dejará de estar vigente en la fecha que indiques.</p>
            {plateFields}
          </fieldset>

          <fieldset>
            <legend>Historial de placas</legend>
            <div className="table-scroll"><table>
              <thead>
                <tr>
                  <th>Placa</th>
                  <th>Estado</th>
                  <th>Desde</th>
                  <th>Hasta</th>
                </tr>
              </thead>
              <tbody>
                {unit.plate_history.length === 0 && (
                  <tr>
                    <td colSpan={4}>Sin placas.</td>
                  </tr>
                )}
                {unit.plate_history.map((entry) => (
                  <tr key={`${entry.identifier}-${entry.start_date}`}>
                    <td>{entry.identifier}</td>
                    <td>{entry.state}</td>
                    <td>{entry.start_date}</td>
                    <td>{entry.end_date ?? "Vigente"}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </fieldset>
        </>
      ) : (
        <fieldset>
          <legend>Placa</legend>
          {plateFields}
        </fieldset>
      )}

      {operatorsSection}

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
