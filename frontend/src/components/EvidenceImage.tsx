"use client";

import { useEffect, useRef, useState } from "react";
import { fetchBlob } from "@/lib/http";

// A report photo. It is protected by the session, so it is downloaded with fetch and shown
// from a temporary local URL; clicking it opens the full size over the page, with a close button.
export default function EvidenceImage({ path, name }: { path: string; name: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let url: string | null = null;
    let cancelled = false;
    fetchBlob(path).then((blob) => {
      if (cancelled) return;
      if (!blob) {
        setFailed(true);
        return;
      }
      url = URL.createObjectURL(blob);
      setSrc(url);
    });
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [path]);

  // While the large view is open: Escape closes it, the page behind does not scroll
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (failed) return <span className="thumb thumb-missing">No se pudo cargar «{name}»</span>;
  if (!src) return <span className="thumb thumb-missing">Cargando…</span>;
  return (
    <>
      <button type="button" className="thumb thumb-button" onClick={() => setOpen(true)} title={`${name} (ver en grande)`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={name} />
      </button>
      {open && (
        <div className="lightbox" role="dialog" aria-modal="true" aria-label={name} onClick={() => setOpen(false)}>
          <button ref={closeButton} type="button" className="lightbox-close" onClick={() => setOpen(false)}>
            Cerrar
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt={name} onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </>
  );
}
