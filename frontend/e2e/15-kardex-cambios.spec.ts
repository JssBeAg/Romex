import { expect, test } from "@playwright/test";
import { loginOk } from "./helpers";

// Lo que se corrige o cambia de una unidad queda en su kardex, con el antes y el después.
test("el kardex muestra la corrección del kilometraje de la unidad", async ({ page }) => {
  const nuevo = 20000 + (Date.now() % 9000);
  await loginOk(page, "G1");

  // Se corrige el kilometraje de E2E-1 desde la pantalla de unidades
  await page.goto("/unidades");
  await page.getByLabel(/Buscar/).fill("E2E-1");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("link", { name: "Editar" }).click();
  await expect(page.locator("#mileage")).not.toHaveValue("");
  const antes = await page.locator("#mileage").inputValue();
  await page.locator("#mileage").fill(String(nuevo));
  await page.getByRole("button", { name: "Guardar" }).click();
  await expect(page).toHaveURL(/\/unidades$/);

  // Y aparece en su kardex como «Cambio de datos»
  await page.goto("/kardex");
  await page.getByLabel(/Buscar/).fill("E2E-1");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("link", { name: "Ver kardex" }).click();
  const fila = page.getByRole("row", { name: /Cambio de datos/ }).filter({ hasText: `Kilometraje: ${antes} → ${nuevo}` });
  await expect(fila.first()).toBeVisible();
  await expect(fila.first()).toContainText("G1");
});

// El kardex trae la tabla de refacciones cambiadas y el detalle de los mantenimientos.
test("el kardex muestra la sección de refacciones cambiadas", async ({ page }) => {
  await loginOk(page, "G1");
  await page.goto("/kardex");
  await page.getByLabel(/Buscar/).fill("E2E-1");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("link", { name: "Ver kardex" }).click();
  await expect(page.getByRole("heading", { name: "Refacciones cambiadas" })).toBeVisible();
});
