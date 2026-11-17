// Today's date as YYYY-MM-DD in the user's own time zone.
// (toISOString() would give the UTC date, which is already "tomorrow" in the evening in México.)
export function today(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}
