// Pieces of the profile picture that does not need a photo: the initials and a colour.

export const AVATAR_TONES = 6;

/** First letter of the first given name + first letter of the paternal surname ("Juan Carlos Pérez" -> "JP"). */
export function initialsOf(firstName: string, paternalSurname: string): string {
  const first = Array.from(firstName.trim())[0] ?? "";
  const last = Array.from(paternalSurname.trim())[0] ?? "";
  const text = `${first}${last}`.toLocaleUpperCase("es-MX");
  return text || "?";
}

/** A colour number (0-5) that always comes out the same for the same enrollment ID. */
export function toneOf(enrollmentId: string): number {
  let hash = 0;
  for (const ch of enrollmentId) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return hash % AVATAR_TONES;
}
