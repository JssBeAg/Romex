"use client";

import { FormEvent, useState } from "react";
import { today } from "@/lib/dates";
import { request } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";
import { type MovementInput, type SparePart, addMovement } from "@/lib/spareParts";

const LABELS: Record<string, string> = {
  movement_type: "Tipo",
  quantity: "Cantidad",
  date: "Fecha",
  note: "Nota",
};

type Props = {
  partId: number;
  onSaved: (part: SparePart) => void; // the part as it is after the movement
};

// Pieces that come in (purchase) or a correction after counting what is on the shelf.
// The pieces that go out are the ones used in maintenances: they are not registered here.
export default function StockMovementForm({ partId, onSaved }: Props) {
  const [type, setType] = useState<MovementInput["movement_type"]>("entrada");
  const [quantity, setQuantity] = useState("");
  const [date, setDate] = useState(today());
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const input: MovementInput = { movement_type: type, quantity, date, note };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => request<{ errors: Record<string, string[]> }>(`refacciones/${partId}/movimientos/?validar=1`, "POST", current),
    labels: LABELS,
  });
  const fieldErrors = feedback.fieldErrors;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const res = await addMovement(partId, input);
    setSubmitting(false);
    if (res.ok && res.data) {
      setQuantity("");
      setNote("");
      onSaved(res.data.spare_part);
      return;
    }
    feedback.rejectResult(res);
  }

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      <fieldset>
        <legend>Registrar entrada o ajuste</legend>
        <p>
          <label htmlFor="movement_type">Tipo</label>
          <br />
          <select id="movement_type" value={type} onChange={(e) => setType(e.target.value as MovementInput["movement_type"])}>
            <option value="entrada">Entrada (compra: suma piezas)</option>
            <option value="ajuste">Ajuste (corrección tras un conteo)</option>
          </select>
          {fieldErrors("movement_type")}
        </p>
        <p>
          <label htmlFor="quantity">
            {type === "ajuste" ? "Piezas a sumar (+) o quitar (−)" : "Piezas que entraron"}
          </label>
          <br />
          <input id="quantity" type="number" step={1} value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          {fieldErrors("quantity")}
        </p>
        <p>
          <label htmlFor="date">Fecha</label>
          <br />
          <input id="date" type="date" max={today()} value={date} onChange={(e) => setDate(e.target.value)} required />
          {fieldErrors("date")}
        </p>
        <p>
          <label htmlFor="note">{type === "ajuste" ? "Motivo del ajuste" : "Nota (proveedor, factura... opcional)"}</label>
          <br />
          <input id="note" value={note} maxLength={255} onChange={(e) => setNote(e.target.value)} required={type === "ajuste"} />
          {fieldErrors("note")}
        </p>
      </fieldset>
      <p>
        <button type="submit" disabled={submitting}>
          {submitting ? "Guardando..." : "Registrar"}
        </button>
      </p>
      {feedback.dialog}
    </form>
  );
}
