"use client";

import { useProtectedImage } from "@/lib/useProtectedImage";

type Props = {
  photoUrl?: string | null; // API path of the photo; without one a neutral icon is shown
  previewUrl?: string | null; // a local address (a file just chosen, not saved yet); wins over photoUrl
  size?: "sm" | "lg";
  // Only when the picture stands alone. By default it is decorative: the part's name is written next to it.
  label?: string;
};

// The photo of a spare part or, without one (or while it loads), a neutral gear icon in a box.
export default function PartPhoto({ photoUrl, previewUrl, size = "sm", label }: Props) {
  const src = useProtectedImage(photoUrl);
  const shown = previewUrl ?? src;
  const a11y = label ? { role: "img", "aria-label": label } : { "aria-hidden": true };
  return (
    <span className={`part-photo part-photo-${size}`} {...a11y}>
      {shown ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={shown} alt="" />
      ) : (
        <svg viewBox="0 0 24 24" width="55%" height="55%" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" focusable="false">
          <circle cx="12" cy="12" r="3.2" />
          <path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7" />
        </svg>
      )}
    </span>
  );
}
