"use client";

import { initialsOf, toneOf } from "@/lib/avatar";
import { useProtectedImage } from "@/lib/useProtectedImage";

type Props = {
  firstName: string;
  paternalSurname: string;
  enrollmentId: string;
  photoUrl?: string | null; // API path of the photo; without one the initials are shown
  previewUrl?: string | null; // a local address (a file just chosen, not saved yet); wins over photoUrl
  size?: "sm" | "md" | "lg";
  // Only when the picture stands alone (no name written next to it). By default it is
  // decorative: a screen reader already reads the name beside it.
  label?: string;
};

// The person's photo or, when there is none (or it is still loading), their initials in a coloured circle.
export default function Avatar({ firstName, paternalSurname, enrollmentId, photoUrl, previewUrl, size = "md", label }: Props) {
  const src = useProtectedImage(photoUrl);

  const shown = previewUrl ?? src;
  const a11y = label ? { role: "img", "aria-label": label } : { "aria-hidden": true };
  return (
    <span className={`avatar avatar-${size} avatar-tone-${toneOf(enrollmentId)}`} {...a11y}>
      {shown ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={shown} alt="" />
      ) : (
        <span className="avatar-initials">{initialsOf(firstName, paternalSurname)}</span>
      )}
    </span>
  );
}
