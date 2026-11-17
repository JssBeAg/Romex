import { expect, test } from "@playwright/test";
import { loginOk, pdfOpenedByClick } from "./helpers";

test.describe("Dashboard del gerente", () => {
  test.beforeEach(async ({ page }) => {
    await loginOk(page, "G1");
    await page.getByRole("navigation", { name: "Menú principal" }).getByRole("link", { name: "Dashboard" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Dashboard e indicadores" })).toBeVisible();
  });

  test("muestra indicadores y gráficas", async ({ page }) => {
    for (const etiqueta of [
      "Reportes abiertos", "Abiertos sin mecánico", "Preventivo vencido", "Preventivo próximo",
      "Refacciones con stock bajo", "Unidades activas / inactivas", "Costo de mantenimiento",
    ]) {
      await expect(page.locator(".kpi-label", { hasText: etiqueta }).first()).toBeVisible();
    }
    for (const titulo of ["Reportes de falla por mes", "Mantenimientos por mes", "Reportes por estatus (hoy)", "Carga de mecánicos (reportes abiertos)"]) {
      await expect(page.getByRole("heading", { level: 2, name: titulo })).toBeVisible();
    }
    await expect(page.locator("p[role='alert']")).toHaveCount(0);
  });

  test("«Reportes abiertos» coincide con los reportes sin cerrar de la lista", async ({ page }) => {
    // Se cuenta aparte, con la lista de reportes (cerrados = Reparado o Sin reparación necesaria)
    const respuesta = await page.request.get("http://localhost:8000/api/reportes-fallas/?page_size=100");
    const { reports } = await respuesta.json();
    const abiertosEnLista = reports.filter(
      (r: { status: { label: string } }) => !["Reparado", "Sin reparación necesaria"].includes(r.status.label)
    ).length;

    const tarjeta = page.locator(".kpi", { hasText: "Reportes abiertos" }).first();
    await expect(tarjeta.locator(".kpi-value")).toHaveText(String(abiertosEnLista));

    await tarjeta.click();
    await expect(page).toHaveURL(/\/reportes/);
  });

  test("cambia el periodo", async ({ page }) => {
    const periodo = page.getByRole("group", { name: "Periodo" });
    await expect(periodo.getByRole("button", { name: "6 meses" })).toHaveAttribute("aria-pressed", "true");
    await periodo.getByRole("button", { name: "3 meses" }).click();
    await expect(periodo.getByRole("button", { name: "3 meses" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("heading", { level: 2, name: "En los últimos 3 meses" })).toBeVisible();
    await periodo.getByRole("button", { name: "12 meses" }).click();
    await expect(page.getByRole("heading", { level: 2, name: "En los últimos 12 meses" })).toBeVisible();
  });

  test("exporta el dashboard a PDF", async ({ page }) => {
    const pdf = await pdfOpenedByClick(page, () => page.getByRole("button", { name: "Exportar a PDF" }).click());
    expect(pdf.head).toBe("%PDF-");
  });
});
