import { expect, test } from "@playwright/test";
import { formError, login } from "./helpers";

// Usa la cuenta F1, creada con cambio obligatorio (se restablece con seed_e2e).
test("la cuenta con cambio obligatorio solo puede cambiar su contraseña", async ({ page }) => {
  await login(page, "F1");
  await expect(page).toHaveURL(/\/cambiar-contrasena/);

  // No hay forma de pasar a otras pantallas
  await page.goto("/reportes");
  await expect(page).toHaveURL(/\/cambiar-contrasena/);
  await expect(page.getByRole("navigation", { name: "Menú principal" }).getByRole("link", { name: "Mis reportes" })).toHaveCount(0);

  const actual = page.getByLabel("Contraseña actual");
  const nueva = page.getByLabel("Contraseña nueva", { exact: true });
  const confirma = page.getByLabel("Confirma la contraseña nueva");

  // Errores mientras escribe
  await actual.fill("Clave12345x");
  await nueva.fill("123");
  await confirma.fill("456");
  await page.getByRole("button", { name: "Cambiar contraseña" }).click();
  await expect(page).toHaveURL(/\/cambiar-contrasena/);
  await expect(page.locator(".field-error").first()).toBeVisible();
  // Al enviar con errores se abre la ventana de errores; se cierra con su botón
  const ventana = page.getByRole("alertdialog");
  await expect(ventana).toBeVisible();
  await ventana.getByRole("button").click();
  await expect(ventana).toHaveCount(0);

  // Con datos válidos: cambia y entra al sistema
  await nueva.fill("NuevaClave9871z");
  await confirma.fill("NuevaClave9871z");
  await page.getByRole("button", { name: "Cambiar contraseña" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("link", { name: "Mis reportes" }).first()).toBeVisible();

  // La contraseña nueva es la que sirve
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/login/);
  await login(page, "F1", "Clave12345x");
  await expect(formError(page)).toHaveText("Matrícula o contraseña incorrectas");
  await login(page, "F1", "NuevaClave9871z");
  await expect(page).toHaveURL(/\/$/);
});
