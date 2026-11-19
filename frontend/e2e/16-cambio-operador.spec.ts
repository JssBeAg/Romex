import { expect, type Page, test } from "@playwright/test";
import { loginOk, today } from "./helpers";

// Asignación exclusiva de operador: una unidad tiene un solo operador a la vez y un operador una
// sola unidad. seed_e2e deja E2E-3 con O3 (desde hace 30 días), E2E-4 sin operador y O4 libre.

async function abrirUnidad(page: Page, numero: string) {
  await page.goto("/unidades");
  await page.getByLabel(/Buscar/).fill(numero);
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("link", { name: "Editar" }).click();
  // Espera a que lleguen los operadores del selector
  await expect(page.locator("#economic_number")).toHaveValue(numero);
}

test.describe.serial("Cambio de operador", () => {
  // Recorren varias pantallas (y dos pestañas): en modo desarrollo cada una se compila al primer acceso
  test.describe.configure({ timeout: 90_000 });

  test("el gerente cambia de operador y otra pantalla abierta no puede asignar al mismo operador", async ({ browser }) => {
    const context = await browser.newContext();
    const otra = await context.newPage(); // otra pestaña del gerente, abierta desde antes
    const page = await context.newPage();
    await loginOk(page, "G1");

    // En la otra pestaña, E2E-4 (sin operador) va a recibir a O4, que aún está libre
    await abrirUnidad(otra, "E2E-4");
    await expect(otra.getByText("La unidad no tiene operador.")).toBeVisible();
    // Un operador que ya tiene unidad (O1 con E2E-1) no se ofrece
    await expect(otra.locator("#new_operator option", { hasText: "(O1)" })).toHaveCount(0);
    await otra.locator("#new_operator").selectOption({ label: "O4 Prueba E2E (O4)" });

    // Mientras tanto, E2E-3 cambia de O3 a O4
    await abrirUnidad(page, "E2E-3");
    await expect(page.getByText(/Operador actual: O3 Prueba E2E \(O3\)/)).toBeVisible();
    await page.getByRole("button", { name: "Cambiar de operador" }).click();
    // El operador actual aparece, pero no se puede elegir
    await expect(page.locator("#new_operator option[disabled]")).toHaveText("O3 Prueba E2E (O3) (actual)");
    await page.locator("#new_operator").selectOption({ label: "O4 Prueba E2E (O4)" });
    await expect(page.locator("#operator_date")).toHaveValue(today());
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/unidades$/);

    // La otra pestaña intenta guardar a O4 en E2E-4: el servidor lo rechaza y dice quién la tiene
    await otra.getByRole("button", { name: "Guardar" }).click();
    const ventana = otra.getByRole("alertdialog");
    await expect(ventana).toContainText("O4 Prueba E2E (O4) ya tiene asignada la unidad E2E-3");
    await expect(otra).toHaveURL(/\/unidades\/\d+$/);
    await context.close();
  });

  test("la unidad muestra al operador actual y el historial", async ({ page }) => {
    await loginOk(page, "G1");
    await abrirUnidad(page, "E2E-3");
    await expect(page.getByText(/Operador actual: O4 Prueba E2E \(O4\)/)).toBeVisible();
    const historial = page.locator("table", { has: page.getByRole("columnheader", { name: "Operador" }) });
    await expect(historial.getByRole("row", { name: /O4 Prueba E2E \(O4\)/ })).toContainText("Actual");
    const anterior = historial.getByRole("row", { name: /O3 Prueba E2E \(O3\)/ });
    await expect(anterior).toContainText(today()); // hasta hoy

    // En la lista, la columna Operador muestra uno solo
    await page.goto("/unidades");
    await page.getByLabel(/Buscar/).fill("E2E-3");
    await page.getByRole("button", { name: "Buscar" }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.locator("tbody tr")).toContainText("O4 Prueba E2E (O4)");
    await expect(page.locator("tbody tr")).not.toContainText("O3 Prueba E2E");

    // Y el kardex lo cuenta
    await page.goto("/kardex");
    await page.getByLabel(/Buscar/).fill("E2E-3");
    await page.getByRole("button", { name: "Buscar" }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await page.getByRole("link", { name: "Ver kardex" }).click();
    await page.getByRole("tab", { name: "Operadores y mecánicos" }).click();
    const periodos = page.getByRole("tabpanel");
    await expect(periodos.getByRole("row", { name: /O4 Prueba E2E \(O4\)/ })).toContainText("Actual");
    await expect(periodos.getByRole("row", { name: /O3 Prueba E2E \(O3\)/ })).toContainText(today());
    await page.getByRole("tab", { name: "Línea de tiempo" }).click();
    await expect(page.getByRole("row", { name: /Asignada a O4 Prueba E2E \(O4\)/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Operador O3 Prueba E2E \(O3\) dejó la unidad/ })).toBeVisible();
  });

  test("el operador anterior ya no puede reportar esa unidad y el nuevo sí", async ({ page }) => {
    await loginOk(page, "O3");
    await page.goto("/reportes/nuevo");
    await expect(page.locator("#unit_id")).toBeVisible();
    await expect(page.locator("#unit_id option", { hasText: "E2E-3" })).toHaveCount(0);

    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await loginOk(page, "O4");
    await page.goto("/reportes/nuevo");
    await expect(page.locator("#unit_id option", { hasText: "E2E-3" })).toHaveCount(1);
  });
});
