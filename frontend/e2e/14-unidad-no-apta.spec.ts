import { expect, test } from "@playwright/test";
import { loginOk } from "./helpers";

// Una unidad cuyo diagnóstico dice que NO puede operar no aparece en el formulario de checklist
// (el checklist se hace antes de salir a operar), y una apta sí.
test.describe.serial("Unidad no apta para operar", () => {
  const ubicacion = `Taller externo ${Date.now() % 100000}`;

  test("el operador reporta una falla en su unidad", async ({ page }) => {
    await loginOk(page, "O2");
    await page.goto("/reportes/nuevo");
    const unidad = page.locator("#unit_id option", { hasText: "E2E-2" });
    await page.locator("#unit_id").selectOption((await unidad.getAttribute("value")) as string);
    await page.getByLabel("Ubicación").fill(ubicacion);
    await page.getByLabel("Descripción").fill("Fuga fuerte de aceite; no debe salir a ruta.");
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/reportes$/);
  });

  test("el gerente asigna al mecánico", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/reportes");
    await page.getByRole("row", { name: new RegExp(ubicacion) }).getByRole("link", { name: /Ver|Editar/ }).click();
    const mecanico = page.locator("#assign_mechanic option", { hasText: "M1" });
    await page.locator("#assign_mechanic").selectOption((await mecanico.getAttribute("value")) as string);
    await page.getByRole("button", { name: /Asignar/ }).click();
    await expect(page.getByRole("row", { name: /^Estatus Asignado/ })).toBeVisible();
  });

  test("el mecánico diagnostica: requiere reparación y la unidad NO puede operar", async ({ page }) => {
    await loginOk(page, "M1");
    await page.goto("/diagnosticos/nuevo");
    const reporte = page.locator("#fault_report_id option", { hasText: ubicacion });
    await page.locator("#fault_report_id").selectOption((await reporte.getAttribute("value")) as string);
    await page.getByLabel("Descripción del diagnóstico (causa detallada)").fill("Retén del cárter roto.");
    await page.locator("input[name='requires_repair']").first().check();
    await page.locator("input[name='unit_operable']").nth(1).check(); // «No»
    await page.locator("#severity_id").selectOption({ index: 1 });
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/diagnosticos$/);
  });

  test("al operador ya no le aparece esa unidad en el checklist y se le explica por qué", async ({ page }) => {
    await loginOk(page, "O2");
    await page.goto("/checklists/nuevo");
    await expect(page.getByText("No tienes unidades aptas para operar ahora.")).toBeVisible();
    await expect(page.getByText(/No aparecen por no estar aptas para operar.*E2E-2/)).toBeVisible();
    await expect(page.locator("#unit_id option", { hasText: "E2E-2" })).toHaveCount(0);
  });

  test("a otro operador, con su unidad apta, sí le aparece", async ({ page }) => {
    await loginOk(page, "O1");
    await page.goto("/checklists/nuevo");
    await expect(page.locator("#unit_id option", { hasText: "E2E-1" })).toHaveCount(1);
    await expect(page.getByText(/No aparecen por no estar aptas/)).toHaveCount(0);
  });
});
