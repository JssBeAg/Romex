"use client";

import { useState } from "react";
import ErrorDialog from "@/components/ErrorDialog";
import { openPdf, type ListParams } from "@/lib/listing";

type Props = {
  path: string; // what to export, relative to /api/ (a list, or one record)
  params?: ListParams; // the filters of the list on screen
  label?: string;
};

// Opens in a new tab the PDF of a list (with the filters on screen) or of one record
export default function ExportButton({ path, params = {}, label = "Exportar a PDF" }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleClick() {
    setBusy(true);
    const problem = await openPdf(path, params);
    setBusy(false);
    if (problem) setError(problem);
  }

  return (
    <>
      <button type="button" onClick={handleClick} disabled={busy}>
        {busy ? "Generando PDF…" : label}
      </button>
      {error && <ErrorDialog title="No se pudo exportar" messages={[error]} onClose={() => setError("")} />}
    </>
  );
}
