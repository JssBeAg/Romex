"use client";

import { useEffect, useState } from "react";
import { fetchBlob } from "@/lib/http";

// Photos are protected by the session, so they are downloaded with fetch and shown from a
// temporary local address. The API path carries the photo's version (?v=), so the local
// address can be kept and reused by every picture that shows the same photo.
const loaded = new Map<string, string>();

/** The displayable address of a protected photo, or null while it loads or when there is none. */
export function useProtectedImage(photoUrl?: string | null): string | null {
  const [src, setSrc] = useState<string | null>(photoUrl ? loaded.get(photoUrl) ?? null : null);

  useEffect(() => {
    if (!photoUrl) {
      setSrc(null);
      return;
    }
    const known = loaded.get(photoUrl);
    if (known) {
      setSrc(known);
      return;
    }
    let cancelled = false;
    fetchBlob(photoUrl).then((blob) => {
      if (cancelled || !blob) return;
      const url = URL.createObjectURL(blob);
      loaded.set(photoUrl, url);
      setSrc(url);
    });
    return () => {
      cancelled = true;
    };
  }, [photoUrl]);

  return src;
}
