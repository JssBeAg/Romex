import { expect, test } from "@playwright/test";
import { loginOk, pdfOpenedByClick } from "./helpers";

// Las listas del gerente: paginación, orden, búsqueda, filtros y exportación a PDF.
// Se usa Refacciones porque el sistema trae 30 de fábrica (hay más de una página).
test.describe("Listas", () => {
  test.beforeEach(async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/refacciones");
    await expect(page.getByRole("heading", { name: "Refacciones" })).toBeVisible();
  });

  test("pagina de 20 en 20 y cambia de página", async ({ page }) => {
    const paginacion = page.getByRole("navigation", { name: "Paginación" });
    await expect(paginacion).toContainText(/1-20 de \d+/);
    await expect(page.locator("tbody tr")).toHaveCount(20);

    await paginacion.getByRole("button", { name: "Siguiente" }).click();
    await expect(paginacion).toContainText(/21-\d+ de \d+/);
    await expect(paginacion.getByRole("button", { name: "Anterior" })).toBeEnabled();
    expect(await page.locator("tbody tr").count()).toBeLessThan(20 + 1);

    await paginacion.getByRole("button", { name: "Anterior" }).click();
    await expect(paginacion).toContainText(/1-20 de \d+/);
  });

  test("ordena por columna en los dos sentidos", async ({ page }) => {
    const nombre = page.getByRole("columnheader", { name: /Nombre/ });
    const primera = () => page.locator("tbody tr").first().locator("td").first().innerText();

    // La lista llega ordenada por nombre; un clic en la columna activa invierte el orden
    await expect(nombre).toHaveAttribute("aria-sort", "ascending");
    // Espera a que lleguen los datos: antes la tabla dice "No hay refacciones." y eso no es una fila
    await expect(page.locator("tbody tr")).toHaveCount(20);
    const asc = await primera();

    await nombre.getByRole("button").click();
    await expect(nombre).toHaveAttribute("aria-sort", "descending");
    await expect.poll(primera).not.toBe(asc);

    await nombre.getByRole("button").click();
    await expect(nombre).toHaveAttribute("aria-sort", "ascending");
    await expect.poll(primera).toBe(asc);

    // Otra columna: empieza en ascendente
    const existencias = page.getByRole("columnheader", { name: /Existencias/ });
    await existencias.getByRole("button").click();
    await expect(existencias).toHaveAttribute("aria-sort", /ascending|descending/);
    await expect(nombre).toHaveAttribute("aria-sort", "none");
  });

  test("busca y avisa cuando no hay resultados", async ({ page }) => {
    await page.getByLabel("Buscar (nombre o descripción)").fill("zzzzzzzz");
    await page.getByRole("button", { name: "Buscar" }).click();
    await expect(page.getByText("No hay refacciones.")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Paginación" })).toContainText("Sin registros");
  });

  test("el filtro «Solo stock bajo» reduce la lista", async ({ page }) => {
    const paginacion = page.getByRole("navigation", { name: "Paginación" });
    await expect(paginacion).toContainText(/1-20 de \d+/);
    await page.getByLabel("Solo stock bajo").check();
    await expect(paginacion).not.toContainText(/1-20 de/);
  });

  test("exporta a PDF lo que se está viendo", async ({ page }) => {
    const pdf = await pdfOpenedByClick(page, () => page.getByRole("button", { name: "Exportar a PDF" }).click());
    expect(pdf.head).toBe("%PDF-");
  });
});

test.describe("Otras listas del gerente", () => {
  const pantallas = [
    { ruta: "/trabajadores", titulo: "Trabajadores" },
    { ruta: "/unidades", titulo: "Unidades" },
    { ruta: "/reportes", titulo: "Reportes de fallas" },
    { ruta: "/mantenimientos", titulo: "Mantenimientos" },
    { ruta: "/diagnosticos", titulo: "Diagnósticos" },
    { ruta: "/checklists", titulo: "Checklists" },
    { ruta: "/kardex", titulo: "Kardex" },
    { ruta: "/preventivo", titulo: "Mantenimiento preventivo" },
    { ruta: "/bitacora", titulo: "Bitácora" },
  ];

  for (const { ruta, titulo } of pantallas) {
    test(`${ruta} carga y exporta a PDF`, async ({ page }) => {
      await loginOk(page, "G1");
      await page.goto(ruta);
      await expect(page.getByRole("heading", { level: 1, name: new RegExp(titulo, "i") })).toBeVisible();
      await expect(page.locator("p[role='alert']")).toHaveCount(0);
      const pdf = await pdfOpenedByClick(page, () => page.getByRole("button", { name: /Exportar|PDF/ }).first().click());
      expect(pdf.head).toBe("%PDF-");
    });
  }
});
