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
  operators: "Operadores asignados",
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

  // Changes to the operators, applied when the form is saved
  const [addOps, setAddOps] = useState<{ operator_id: string; start_date: string }[]>([]);
  const [endOps, setEndOps] = useState<Record<number, string>>({}); // assignment id -> end date
  const [newOperatorId, setNewOperatorId] = useState("");
  const [newOperatorStart, setNewOperatorStart] = useState(today());

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
    add_operators: addOps.map((entry) => ({
      operator_id: Number(entry.operator_id),
      start_date: entry.start_date,
    })),
    end_operators: Object.entries(endOps).map(([id, date]) => ({
      assignment_id: Number(id),
      end_date: date,
    })),
  };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("unidades", unit?.id ?? null, current),
    labels: LABELS,
  });

  useEffect(() => {
    getUnitCatalogs().then((res) => {
      if (res.ok && res.data) setCatalogs(res.data);
      else setGeneralError(res.error ?? "No se pudieron cargar los catálogos");
    });
  }, []);

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

  // Operators that can still be added: not assigned now (unless that is being ended) nor already in the list
  const assignedNow = new Set(
    (unit?.operators ?? [])
      .filter((a) => a.end_date === null && endOps[a.id] === undefined)
      .map((a) => a.operator.id)
  );
  const availableOperators = (catalogs?.operators ?? []).filter(
    (o) => !assignedNow.has(o.id) && !addOps.some((entry) => entry.operator_id === String(o.id))
  );

  function addOperator() {
    if (!newOperatorId) return;
    setAddOps((previous) => [...previous, { operator_id: newOperatorId, start_date: newOperatorStart }]);
    setNewOperatorId("");
    feedback.touch("operators");
  }

  function startEnding(assignmentId: number) {
    setEndOps((previous) => ({ ...previous, [assignmentId]: today() }));
    feedback.touch("operators");
  }

  function undoEnding(assignmentId: number) {
    setEndOps((previous) => {
      const next = { ...previous };
      delete next[assignmentId];
      return next;
    });
  }

  const operatorsSection = (
    <fieldset>
      <legend>Operadores asignados</legend>
      <div className="span-all">
        <p className="hint">
          Una unidad puede tener varios operadores a la vez, y un operador varias unidades. Solo los
          operadores asignados pueden reportar fallas y llenar checklists de la unidad. Los cambios
          se aplican al guardar.
        </p>

        {unit && unit.operators.length > 0 && (
          <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Operador</th>
                <th>Desde</th>
                <th>Hasta</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {unit.operators.map((assignment) => {
                const active = assignment.end_date === null;
                const pendingEnd = endOps[assignment.id];
                return (
                  <tr key={assignment.id}>
                    <td>{assignment.operator.label}</td>
                    <td>{assignment.start_date}</td>
                    <td>
                      {!active ? (
                        assignment.end_date
                      ) : pendingEnd !== undefined ? (
                        <input
                          type="date"
                          aria-label={`Fecha de fin de ${assignment.operator.label}`}
                          data-field="operators"
                          min={assignment.start_date}
                          max={today()}
                          value={pendingEnd}
                          onChange={(e) =>
                            setEndOps((previous) => ({ ...previous, [assignment.id]: e.target.value }))
                          }
                        />
                      ) : (
                        "Vigente"
                      )}
                    </td>
                    <td>
                      {active &&
                        (pendingEnd === undefined ? (
                          <button type="button" onClick={() => startEnding(assignment.id)}>
                            Terminar asignación
                          </button>
                        ) : (
                          <button type="button" onClick={() => undoEnding(assignment.id)}>
                            Deshacer
                          </button>
                        ))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        )}
        {unit && unit.operators.length === 0 && <p>La unidad no ha tenido operadores asignados.</p>}

        {addOps.map((entry, index) => (
          <div key={entry.operator_id} className="assign-row">
            <strong>
              {catalogs?.operators.find((o) => String(o.id) === entry.operator_id)?.label ?? "Operador"}
            </strong>
            <label>
              Desde{" "}
              <input
                type="date"
                data-field="operators"
                max={today()}
                value={entry.start_date}
                onChange={(e) =>
                  setAddOps((previous) =>
                    previous.map((item, i) => (i === index ? { ...item, start_date: e.target.value } : item))
                  )
                }
              />
            </label>
            <button type="button" onClick={() => setAddOps((previous) => previous.filter((_, i) => i !== index))}>
              Quitar
            </button>
          </div>
        ))}

        <div className="assign-row">
          <select
            id="new_operator"
            aria-label="Operador a asignar"
            data-field="operators"
            value={newOperatorId}
            onChange={(e) => setNewOperatorId(e.target.value)}
          >
            <option value="">Elige un operador</option>
            {availableOperators.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            type="date"
            aria-label="Fecha de inicio de la asignación"
            data-field="operators"
            max={today()}
            value={newOperatorStart}
            onChange={(e) => setNewOperatorStart(e.target.value)}
          />
          <button type="button" onClick={addOperator} disabled={!newOperatorId}>
            Agregar operador
          </button>
        </div>
        {fieldErrors("operators")}
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
