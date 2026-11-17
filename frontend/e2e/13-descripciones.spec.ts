import { expect, test } from "@playwright/test";
import { loginOk } from "./helpers";

// La descripción del reporte se ve en el diagnóstico, y la del diagnóstico, en el mantenimiento.
test.describe.serial("Descripciones a lo largo del flujo", () => {
  const sello = Date.now() % 100000;
  const ubicacion = `Libramiento ${sello}`;
  const descripcionReporte = `Vibra el volante al frenar a más de 80 km/h (${sello}).`;
  const descripcionDiagnostico = `Discos de freno alabeados y balatas gastadas (${sello}).`;

  test("el operador crea el reporte", async ({ page }) => {
    await loginOk(page, "O1");
    await page.goto("/reportes/nuevo");
    const unidad = page.locator("#unit_id option", { hasText: "E2E-1" });
    await page.locator("#unit_id").selectOption((await unidad.getAttribute("value")) as string);
    await page.getByLabel("Ubicación").fill(ubicacion);
    await page.getByLabel("Descripción").fill(descripcionReporte);
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

  test("al diagnosticar, el mecánico lee la descripción del reporte elegido", async ({ page }) => {
    await loginOk(page, "M1");
    await page.goto("/diagnosticos/nuevo");
    await expect(page.getByText("Descripción del reporte")).toHaveCount(0); // aún no eligió
    const reporte = page.locator("#fault_report_id option", { hasText: ubicacion });
    await page.locator("#fault_report_id").selectOption((await reporte.getAttribute("value")) as string);
    await expect(page.getByText(descripcionReporte)).toBeVisible();

    await page.getByLabel("Descripción del diagnóstico (causa detallada)").fill(descripcionDiagnostico);
    await page.locator("input[name='requires_repair']").first().check();
    await page.locator("input[name='unit_operable']").first().check(); // «Sí»: esta unidad sigue apta para operar
    await page.locator("#severity_id").selectOption({ index: 1 });
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/diagnosticos$/);
  });

  test("el gerente ve ambas descripciones en la ficha del diagnóstico", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/diagnosticos");
    await page.getByRole("row", { name: /E2E-1/ }).getByRole("link", { name: /Ver|Editar/ }).first().click();
    await expect(page.getByRole("row", { name: /Descripción del reporte/ })).toContainText(descripcionReporte);
    await expect(page.getByRole("row", { name: /Descripción del diagnóstico/ })).toContainText(descripcionDiagnostico);
  });

  test("al crear el mantenimiento, el mecánico lee la descripción del diagnóstico elegido", async ({ page }) => {
    await loginOk(page, "M1");
    await page.goto("/mantenimientos/nuevo");
    await page.locator("#service_type_id").selectOption({ label: "Correctivo" });
    await expect(page.getByText("Descripción del diagnóstico")).toHaveCount(0); // aún no eligió
    const diagnostico = page.locator("#diagnosis_id option").filter({ hasNotText: "---------" }).first();
    await page.locator("#diagnosis_id").selectOption((await diagnostico.getAttribute("value")) as string);
    await expect(page.getByText(descripcionDiagnostico)).toBeVisible();
  });
});
