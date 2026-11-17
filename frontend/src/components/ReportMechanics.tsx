"use client";

import { useEffect, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import type { Option } from "@/lib/http";
import { today } from "@/lib/dates";
import {
  type MechanicAssignment,
  type Report,
  assignMechanic,
  endMechanicAssignment,
  getReportCatalogs,
} from "@/lib/reports";

type Props = {
  report: Report;
  onChange: (report: Report) => void; // the report as the server returns it after a change
};

// Manager only: who works on the report, and since/until when. Changes are saved at once.
export default function ReportMechanics({ report, onChange }: Props) {
  const [mechanics, setMechanics] = useState<Option[]>([]);
  const [mechanicId, setMechanicId] = useState("");
  const [startDate, setStartDate] = useState(today());
  const [endDates, setEndDates] = useState<Record<number, string>>({});
  const [working, setWorking] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    getReportCatalogs().then((res) => {
      if (res.ok && res.data?.mechanics) setMechanics(res.data.mechanics);
    });
  }, []);

  const assignments: MechanicAssignment[] = report.mechanics ?? [];
  const current = assignments.filter((a) => a.end_date === null);
  const past = assignments.filter((a) => a.end_date !== null);
  const available = mechanics.filter((m) => !current.some((a) => a.mechanic.id === m.id));

  function fail(res: { errors?: Record<string, string[]>; error?: string }) {
    const list = Object.values(res.errors ?? {}).flat();
    setErrors(list.length > 0 ? list : [res.error ?? "No se pudo guardar el cambio."]);
  }

  async function handleAssign() {
    if (!mechanicId) {
      setErrors(["Elige un mecánico."]);
      return;
    }
    setWorking(true);
    const res = await assignMechanic(report.id, Number(mechanicId), startDate);
    setWorking(false);
    if (res.ok && res.data) {
      onChange(res.data.report);
      setMechanicId("");
    } else {
      fail(res);
    }
  }

  async function handleEnd(assignment: MechanicAssignment) {
    setWorking(true);
    const res = await endMechanicAssignment(report.id, assignment.id, endDates[assignment.id] ?? today());
    setWorking(false);
    if (res.ok && res.data) onChange(res.data.report);
    else fail(res);
  }

  return (
    <section aria-labelledby="mechanics-title">
      <h2 id="mechanics-title">Mecánicos asignados</h2>
      <p className="hint">
        Solo los mecánicos asignados pueden ver este reporte, diagnosticarlo y repararlo.
      </p>

      {current.length === 0 ? (
        <p>Ningún mecánico asignado: el reporte no es visible para los mecánicos.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mecánico</th>
                <th>Desde</th>
                <th>Terminar asignación</th>
              </tr>
            </thead>
            <tbody>
              {current.map((a) => (
                <tr key={a.id}>
                  <td>{a.mechanic.label}</td>
                  <td>{a.start_date}</td>
                  <td>
                    <input
                      type="date"
                      aria-label={`Fecha de fin de ${a.mechanic.label}`}
                      min={a.start_date}
                      max={today()}
                      value={endDates[a.id] ?? today()}
                      onChange={(e) => setEndDates((previous) => ({ ...previous, [a.id]: e.target.value }))}
                    />{" "}
                    <button type="button" disabled={working} onClick={() => handleEnd(a)}>
                      Terminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {report.can_assign ? (
        <div className="assign-row">
          <label htmlFor="assign_mechanic">Asignar mecánico</label>
          <select id="assign_mechanic" value={mechanicId} onChange={(e) => setMechanicId(e.target.value)}>
            <option value="">---------</option>
            {available.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          <label htmlFor="assign_start">Desde</label>
          <input
            id="assign_start"
            type="date"
            max={today()}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <button type="button" disabled={working} onClick={handleAssign}>
            Asignar
          </button>
        </div>
      ) : (
        <p>El reporte ya está cerrado: no se pueden asignar más mecánicos.</p>
      )}

      {past.length > 0 && (
        <>
          <h3>Historial de asignaciones</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Mecánico</th>
                  <th>Desde</th>
                  <th>Hasta</th>
                </tr>
              </thead>
              <tbody>
                {past.map((a) => (
                  <tr key={a.id}>
                    <td>{a.mechanic.label}</td>
                    <td>{a.start_date}</td>
                    <td>{a.end_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {errors.length > 0 && (
        <ErrorDialog title="No se pudo guardar" messages={errors} onClose={() => setErrors([])} />
      )}
    </section>
  );
}
