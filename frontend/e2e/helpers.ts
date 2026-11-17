import { expect, type Download, type Page } from "@playwright/test";

export const PASSWORD = "Clave12345x";

/** Inicia sesión por la pantalla de acceso, como lo haría una persona. */
export async function login(page: Page, enrollmentId: string, password = PASSWORD) {
  await page.goto("/login");
  // Espera a que la página termine de cargar (si se envía antes, el formulario no responde)
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Matrícula").fill(enrollmentId);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar" }).click();
}

/** Inicia sesión y espera a estar dentro (la página de inicio). */
export async function loginOk(page: Page, enrollmentId: string, password = PASSWORD) {
  await login(page, enrollmentId, password);
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
}

export function today() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Mexico_City" }).format(new Date());
}

/** El mensaje de error del formulario (no el anunciador de rutas de Next, que también es role="alert"). */
export function formError(page: Page) {
  return page.locator("p[role='alert']");
}

/**
 * Hace el clic y devuelve los primeros bytes del PDF que se abre en la pestaña nueva.
 * En una pestaña normal el navegador muestra el PDF (la dirección es blob:); el Chromium sin
 * pantalla de las pruebas no tiene visor y lo guarda como descarga: en los dos casos se lee el archivo.
 */
export async function pdfOpenedByClick(page: Page, click: () => Promise<void>) {
  let saved: Download | null = null;
  page.on("popup", (tab) => tab.on("download", (d) => (saved = d)));
  const popup = page.waitForEvent("popup");
  await click();
  const tab = await popup;
  await expect
    .poll(() => saved !== null || tab.url().startsWith("blob:"), { timeout: 15000 })
    .toBeTruthy();
  if (saved) {
    const { readFileSync } = await import("node:fs");
    const path = await (saved as Download).path();
    return { head: readFileSync(path!).subarray(0, 5).toString(), name: (saved as Download).suggestedFilename() };
  }
  const head = await tab.evaluate(async (u) => {
    const r = await fetch(u);
    return new TextDecoder().decode((await r.arrayBuffer()).slice(0, 5));
  }, tab.url());
  return { head, name: "" };
}
