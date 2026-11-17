"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import EvidenceImage from "@/components/EvidenceImage";
import { type ApiResult, validateOnServer } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import {
  IMAGE_TYPES,
  MAX_IMAGES,
  MAX_IMAGE_MB,
  type Report,
  type ReportCatalogs,
  type ReportInput,
  getReportCatalogs,
} from "@/lib/reports";
import { today } from "@/lib/dates";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  unit_id: "Unidad",
  location: "Ubicación",
  date: "Fecha",
  description: "Descripción",
  images: "Evidencia",
};

type Props = {
  report?: Report; // present when editing
  onSubmit: (input: ReportInput) => Promise<ApiResult<{ report: Report }>>;
  onSaved: () => void;
  onCancel: () => void;
};


export default function ReportForm({ report, onSubmit, onSaved, onCancel }: Props) {
  const [unitId, setUnitId] = useState(report ? String(report.unit.id) : "");
  const [location, setLocation] = useState(report?.location ?? "");
  const [date, setDate] = useState(report?.date ?? today());
  const [newFiles, setNewFiles] = useState<File[]>([]); // photos to attach
  const [removeIds, setRemoveIds] = useState<number[]>([]); // attached photos to remove
  const [photoMessage, setPhotoMessage] = useState("");
  const [description, setDescription] = useState(report?.description ?? "");

  const [catalogs, setCatalogs] = useState<ReportCatalogs | null>(null);
  const [generalError, setGeneralError] = useState(""); // the catalogs could not be loaded
  const [submitting, setSubmitting] = useState(false);

  // The server checks the text fields while they are filled in (the photos are checked here)
  const feedback = useFormFeedback({
    payload: {
      unit_id: unitId ? Number(unitId) : null,
      location,
      date,
      description,
      remove_evidence_ids: removeIds,
    },
    validate: (current) => validateOnServer("reportes-fallas", report?.id ?? null, current),
    labels: LABELS,
  });

  useEffect(() => {
    getReportCatalogs().then((res) => {
      if (res.ok && res.data) setCatalogs(res.data);
      else setGeneralError(res.error ?? "No se pudieron cargar los catálogos");
    });
  }, []);

  // Temporary local URLs to preview the photos chosen but not saved yet
  const previews = useMemo(() => newFiles.map((file) => URL.createObjectURL(file)), [newFiles]);
  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews]);

  // The operator's assigned units, plus the one this report already has (it may no longer be theirs)
  const unitOptions = [...(catalogs?.units ?? [])];
  if (report && catalogs && !unitOptions.some((option) => option.id === report.unit.id)) {
    unitOptions.unshift(report.unit);
  }
  const noUnits = !report && catalogs !== null && unitOptions.length === 0;

  const keptCount = (report?.evidence.length ?? 0) - removeIds.length;
  const freeSlots = MAX_IMAGES - keptCount - newFiles.length;

  function handleFiles(e: ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(e.target.files ?? []);
    e.target.value = ""; // so the same file can be chosen again later
    const accepted: File[] = [];
    const problems: string[] = [];
    for (const file of chosen) {
      if (!IMAGE_TYPES.includes(file.type)) problems.push(`«${file.name}» no es JPG, PNG ni WebP.`);
      else if (file.size > MAX_IMAGE_MB * 1024 * 1024)
        problems.push(`«${file.name}» pesa más de ${MAX_IMAGE_MB} MB.`);
      else if (accepted.length >= freeSlots) problems.push(`«${file.name}»: máximo ${MAX_IMAGES} imágenes por reporte.`);
      else accepted.push(file);
    }
    setPhotoMessage(problems.join(" "));
    if (accepted.length > 0) setNewFiles((previous) => [...previous, ...accepted]);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    setSubmitting(true);
    const res = await onSubmit({
      unit_id: unitId ? Number(unitId) : null,
      location,
      date,
      description,
      images: newFiles,
      remove_evidence_ids: removeIds,
    });
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
        <legend>Datos del reporte</legend>
        {report && (
          <p>
            Estatus: {report.status.label}
          </p>
        )}
        <p>
          <label htmlFor="unit_id">Unidad</label>
          <br />
          <select id="unit_id" value={unitId} onChange={(e) => setUnitId(e.target.value)} required>
            <option value="">---------</option>
            {unitOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          {noUnits && (
            <div className="hint">No tienes unidades asignadas. Pide al gerente que te asigne una.</div>
          )}
          {fieldErrors("unit_id")}
        </p>
        <p>
          <label htmlFor="location">Ubicación</label>
          <br />
          <input id="location" value={location} maxLength={255} onChange={(e) => setLocation(e.target.value)} required />
          {fieldErrors("location")}
        </p>
        <p>
          <label htmlFor="date">Fecha</label>
          <br />
          <input id="date" type="date" max={today()} value={date} onChange={(e) => setDate(e.target.value)} required />
          {fieldErrors("date")}
        </p>
        <div style={{ gridColumn: "1 / -1" }}>
          <label htmlFor="images">
            Evidencia (fotos, opcional: hasta {MAX_IMAGES} de {MAX_IMAGE_MB} MB, JPG, PNG o WebP)
          </label>
          {report && report.evidence.length > 0 && (
            <div className="thumb-grid">
              {report.evidence.map((photo) => {
                const removed = removeIds.includes(photo.id);
                return (
                  <div key={photo.id} className="thumb-item">
                    <div className={removed ? "thumb-removed" : undefined}>
                      <EvidenceImage path={photo.url} name={photo.name} />
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setRemoveIds((previous) =>
                          removed ? previous.filter((id) => id !== photo.id) : [...previous, photo.id]
                        )
                      }
                    >
                      {removed ? "Conservar" : "Quitar"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
          {newFiles.length > 0 && (
            <div className="thumb-grid">
              {newFiles.map((file, index) => (
                <div key={`${file.name}-${index}`} className="thumb-item">
                  <span className="thumb">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={previews[index]} alt={file.name} />
                  </span>
                  <button type="button" onClick={() => setNewFiles((previous) => previous.filter((_, i) => i !== index))}>
                    Quitar
                  </button>
                </div>
              ))}
            </div>
          )}
          {freeSlots > 0 ? (
            <p>
              <input id="images" type="file" accept={IMAGE_TYPES.join(",")} multiple onChange={handleFiles} />
            </p>
          ) : (
            <p className="hint">Ya tienes {MAX_IMAGES} imágenes, el máximo. Quita alguna para agregar otra.</p>
          )}
          {photoMessage && <div role="alert">{photoMessage}</div>}
          {fieldErrors("images")}
        </div>
        <p>
          <label htmlFor="description">Descripción</label>
          <br />
          <textarea id="description" rows={6} cols={60} value={description} onChange={(e) => setDescription(e.target.value)} required />
          {fieldErrors("description")}
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
