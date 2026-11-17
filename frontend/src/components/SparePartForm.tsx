"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import PartPhoto from "@/components/PartPhoto";
import { type ApiResult, type FieldErrors, validateOnServer } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import { type SparePart, type SparePartInput, deletePartPhoto, uploadPartPhoto } from "@/lib/spareParts";
import { PHOTO_MAX_MB, PHOTO_TYPES, photoProblem } from "@/lib/workers";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  name: "Nombre",
  description: "Descripción",
  unit_price: "Precio unitario de referencia",
  min_stock: "Existencia mínima",
  is_active: "Activa",
  initial_stock: "Existencias iniciales",
  photo: "Fotografía",
};

type Props = {
  part?: SparePart; // present when editing
  onSubmit: (input: SparePartInput) => Promise<ApiResult<{ spare_part: SparePart }>>;
  onSaved: (part: SparePart) => void;
  onCancel: () => void;
};

export default function SparePartForm({ part, onSubmit, onSaved, onCancel }: Props) {
  const editing = part !== undefined;
  const [name, setName] = useState(part?.name ?? "");
  const [description, setDescription] = useState(part?.description ?? "");
  const [price, setPrice] = useState(part?.unit_price ?? "");
  const [minStock, setMinStock] = useState(part ? String(part.min_stock) : "0");
  const [isActive, setIsActive] = useState(part?.is_active ?? true);
  const [initialStock, setInitialStock] = useState("0");
  const [submitting, setSubmitting] = useState(false);

  // Photo (optional): a file chosen but not sent yet, or the wish to remove the current one
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [photoWarning, setPhotoWarning] = useState(""); // the part was saved but the photo was not
  const [savedPart, setSavedPart] = useState<SparePart | null>(null);
  const photoInput = useRef<HTMLInputElement>(null);

  const input: SparePartInput = {
    name,
    description,
    unit_price: price,
    min_stock: minStock,
    is_active: isActive,
    initial_stock: editing ? "0" : initialStock,
  };
  const photoError = photoFile ? photoProblem(photoFile) : "";
  const localErrors: FieldErrors = photoError ? { photo: [photoError] } : {};
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("refacciones", part?.id ?? null, current),
    localErrors,
    labels: LABELS,
  });
  const fieldErrors = feedback.fieldErrors;

  // A local address to preview the chosen photo (released when it changes)
  useEffect(() => {
    if (!photoFile || photoProblem(photoFile)) {
      setPhotoPreview(null);
      return;
    }
    const url = URL.createObjectURL(photoFile);
    setPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photoFile]);

  function choosePhoto(file: File | null) {
    setPhotoFile(file);
    if (file) setRemovePhoto(false);
  }

  function clearPhoto() {
    setPhotoFile(null);
    if (photoInput.current) photoInput.current.value = "";
    // With a saved photo, "remove" also means taking it off when the form is saved
    if (part?.photo_url) setRemovePhoto(true);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (feedback.localHasErrors) {
      feedback.rejectKnown();
      return;
    }
    setSubmitting(true);
    const res = await onSubmit(input);
    if (!res.ok || !res.data) {
      setSubmitting(false);
      feedback.rejectResult(res);
      return;
    }
    // The part is saved; now the photo (optional) goes up, or the old one is removed
    let saved = res.data.spare_part;
    if (photoFile || (removePhoto && part?.photo_url)) {
      const photoResult = photoFile
        ? await uploadPartPhoto(saved.id, photoFile)
        : await deletePartPhoto(saved.id);
      if (!photoResult.ok || !photoResult.data) {
        setSubmitting(false);
        setSavedPart(saved);
        setPhotoWarning(photoResult.errors?.photo?.[0] ?? photoResult.error ?? "No se pudo guardar la fotografía.");
        return;
      }
      saved = photoResult.data.spare_part;
    }
    setSubmitting(false);
    setPhotoFile(null);
    setRemovePhoto(false);
    if (photoInput.current) photoInput.current.value = "";
    onSaved(saved);
  }

  const hasSavedPhoto = !!part?.photo_url && !removePhoto;
  const canRemovePhoto = !!photoFile || hasSavedPhoto;
  const partName = name.trim() || "la refacción";

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      {photoWarning && savedPart && (
        <ErrorDialog
          title="La refacción se guardó, pero no la fotografía"
          messages={[photoWarning, "Puedes volver a intentarlo editando la refacción."]}
          onClose={() => {
            setPhotoWarning("");
            onSaved(savedPart);
          }}
        />
      )}
      <fieldset>
        <legend>Datos de la refacción</legend>
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
          <label htmlFor="unit_price">Precio unitario de referencia (MXN, opcional)</label>
          <br />
          <input id="unit_price" type="number" min={0} step={0.01} value={price} onChange={(e) => setPrice(e.target.value)} />
          {fieldErrors("unit_price")}
        </p>
        <p>
          <label htmlFor="min_stock">Existencia mínima (piezas)</label>
          <br />
          <input id="min_stock" type="number" min={0} step={1} value={minStock} onChange={(e) => setMinStock(e.target.value)} required />
          <span className="hint"> Con esta cantidad o menos aparece como «Stock bajo». Con 0 no se avisa.</span>
          {fieldErrors("min_stock")}
        </p>
        <p>
          <label>
            <input id="is_active" type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Activa
          </label>
          <span className="hint"> Una refacción inactiva conserva su historial, pero ya no se puede usar en mantenimientos nuevos.</span>
          {fieldErrors("is_active")}
        </p>
        {!editing && (
          <p>
            <label htmlFor="initial_stock">Existencias iniciales (piezas)</label>
            <br />
            <input id="initial_stock" type="number" min={0} step={1} value={initialStock} onChange={(e) => setInitialStock(e.target.value)} />
            {fieldErrors("initial_stock")}
          </p>
        )}
      </fieldset>

      <fieldset>
        <legend>Fotografía (opcional)</legend>
        <div className="photo-field span-all">
          <PartPhoto
            size="lg"
            photoUrl={hasSavedPhoto ? part?.photo_url : null}
            previewUrl={photoPreview}
            label={
              photoPreview || hasSavedPhoto
                ? `Fotografía de ${partName}`
                : `Sin fotografía de ${partName}`
            }
          />
          <div className="photo-actions">
            <label htmlFor="photo">{canRemovePhoto ? "Cambiar fotografía" : "Elegir fotografía"}</label>
            <input
              id="photo"
              ref={photoInput}
              type="file"
              accept={PHOTO_TYPES.join(",")}
              onChange={(e) => choosePhoto(e.target.files?.[0] ?? null)}
            />
            {canRemovePhoto && (
              <button type="button" onClick={clearPhoto}>
                Quitar fotografía
              </button>
            )}
            {fieldErrors("photo")}
          </div>
        </div>
        <p className="hint span-all">
          JPG, PNG o WebP, de hasta {PHOTO_MAX_MB} MB. Se reduce de tamaño y conserva sus proporciones (no se recorta).
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
