import { expect, type Page, test } from "@playwright/test";
import { loginOk, pdfOpenedByClick } from "./helpers";

// El kardex de una unidad, organizado por tema: una pestaña por sección, cada una con su tabla,
// sus filtros y su PDF. Usa E2E-1: el reporte y el diagnóstico de la prueba 13 y el mantenimiento
// preventivo que crea seed_e2e.

async function abrirKardex(page: Page, numero: string) {
  await page.goto("/kardex");
  await page.getByLabel(/Buscar/).fill(numero);
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("link", { name: "Ver kardex" }).click();
  await expect(page.getByRole("heading", { name: `Kardex de la unidad ${numero}` })).toBeVisible();
}

function panel(page: Page) {
  return page.getByRole("tabpanel");
}

test.describe("Kardex por secciones", () => {
  // Varias pantallas y PDFs: en modo desarrollo cada pantalla se compila al primer acceso
  test.describe.configure({ timeout: 90_000 });

  test("la corrección del kilometraje aparece en «Cambios de datos», en columnas", async ({ page }) => {
    const nuevo = 20000 + (Date.now() % 9000);
    await loginOk(page, "G1");

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

    await abrirKardex(page, "E2E-1");
    await page.getByRole("tab", { name: "Placas y cambios de datos" }).click();
    await expect(page).toHaveURL(/#cambios$/);
    const fila = panel(page).getByRole("row").filter({ hasText: String(nuevo) }).first();
    await expect(fila.getByRole("cell").nth(1)).toHaveText("Kilometraje");
    await expect(fila.getByRole("cell").nth(2)).toHaveText(antes);
    await expect(fila.getByRole("cell").nth(3)).toHaveText(String(nuevo));
    await expect(fila.getByRole("cell").nth(4)).toContainText("G1");
    // La tabla de placas está en la misma pestaña
    await expect(panel(page).getByRole("heading", { name: "Placas" })).toBeVisible();
  });

  test("cada pestaña muestra su propia tabla", async ({ page }) => {
    await loginOk(page, "G1");
    await abrirKardex(page, "E2E-1");
    const columnas: Record<string, string[]> = {
      Mantenimientos: ["Servicio", "Responsables", "Refacciones", "Reparación terminada", "Observaciones"],
      Fallas: ["Descripción", "Estatus", "Causa", "Gravedad", "¿Puede operar?"],
      Checklists: ["Operador", "Resultado", "Viaje"],
      "Refacciones cambiadas": ["Refacción", "Piezas", "Veces", "Último cambio"],
      "Operadores y mecánicos": ["Rol", "Persona", "Desde", "Hasta"],
      "Línea de tiempo": ["Tipo", "Evento", "Detalle"],
    };
    for (const [pestaña, encabezados] of Object.entries(columnas)) {
      await page.getByRole("tab", { name: pestaña, exact: true }).click();
      await expect(page.getByRole("tab", { name: pestaña, exact: true })).toHaveAttribute("aria-selected", "true");
      for (const encabezado of encabezados) {
        await expect(panel(page).getByRole("columnheader", { name: new RegExp(encabezado.replace(/[?¿]/g, ".")) }).first()).toBeVisible();
      }
    }
    // En Fallas está el reporte de la prueba 13, con su diagnóstico en columnas
    await page.getByRole("tab", { name: "Fallas", exact: true }).click();
    await expect(panel(page).locator("tbody tr").first()).not.toContainText("Sin reportes");
  });

  test("filtrar reduce las filas y exportar abre el PDF de la sección y el completo", async ({ page }) => {
    await loginOk(page, "G1");
    await abrirKardex(page, "E2E-1");
    const filas = panel(page).locator("tbody tr");

    // Mantenimientos: el preventivo que crea seed_e2e
    await expect(filas.first()).toContainText("Preventivo");
    const todas = await filas.count();
    expect(todas).toBeGreaterThan(0);

    await panel(page).getByLabel("Tipo de servicio").selectOption("correctivo");
    await panel(page).getByRole("button", { name: "Buscar" }).click();
    await expect(panel(page).getByText("Sin mantenimientos con estos filtros.")).toBeVisible();

    await panel(page).getByLabel("Tipo de servicio").selectOption("preventivo");
    await panel(page).getByRole("button", { name: "Buscar" }).click();
    await expect(filas).toHaveCount(todas);

    await panel(page).getByLabel("Hasta").fill("2000-01-01");
    await panel(page).getByRole("button", { name: "Buscar" }).click();
    await expect(panel(page).getByText("Sin mantenimientos con estos filtros.")).toBeVisible();

    await panel(page).getByRole("button", { name: "Limpiar" }).click();
    await expect(filas).toHaveCount(todas);

    // El PDF de la sección (con sus filtros) y el kardex completo se abren en una pestaña nueva
    const seccion = await pdfOpenedByClick(page, () => panel(page).getByRole("button", { name: "Exportar mantenimientos a PDF" }).click());
    expect(seccion.head).toBe("%PDF-");
    const completo = await pdfOpenedByClick(page, () => page.getByRole("button", { name: "Exportar kardex completo" }).click());
    expect(completo.head).toBe("%PDF-");
  });
});
