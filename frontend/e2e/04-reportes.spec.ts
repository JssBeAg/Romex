import { expect, test } from "@playwright/test";
import { loginOk } from "./helpers";

// Un reporte de falla de principio a fin por pantalla: lo crea el operador,
// el gerente se entera, asigna un mecánico y el mecánico lo ve.
test.describe.serial("Reporte de falla", () => {
  const ubicacion = `Autopista 57 km ${Date.now() % 100000}`;

  test("el operador crea un reporte y lo ve en su lista", async ({ page }) => {
    await loginOk(page, "O1");
    await page.getByRole("navigation", { name: "Menú principal" }).getByRole("link", { name: "Mis reportes" }).click();
    await page.getByRole("link", { name: "Nuevo reporte" }).click();

    const unidad = page.locator("#unit_id option", { hasText: "E2E-1" });
    await page.locator("#unit_id").selectOption((await unidad.getAttribute("value")) as string);
    await page.getByLabel("Ubicación").fill(ubicacion);
    await page.getByLabel("Descripción").fill("Se enciende el testigo del motor y pierde potencia.");
    await page.getByRole("button", { name: "Guardar" }).click();

    await expect(page).toHaveURL(/\/reportes$/);
    const fila = page.getByRole("row", { name: new RegExp(ubicacion) });
    await expect(fila).toContainText("E2E-1");
    await expect(fila).toContainText("Pendiente");
  });

  test("otro operador no ve ese reporte", async ({ page }) => {
    await loginOk(page, "O2");
    await page.goto("/reportes");
    await expect(page.getByRole("heading", { name: "Mis reportes de fallas" })).toBeVisible();
    await expect(page.getByText(ubicacion)).toHaveCount(0);
  });

  test("el gerente recibe el aviso y lo marca como leído", async ({ page }) => {
    await loginOk(page, "G1");
    const campana = page.getByRole("link", { name: /^Notificaciones/ });
    await expect(campana).toHaveAttribute("aria-label", /sin leer/);

    await campana.click();
    await expect(page.getByRole("heading", { name: "Notificaciones" })).toBeVisible();
    await expect(page.getByText(/Nuevo reporte de falla en la unidad E2E-1/).first()).toBeVisible();

    await page.getByRole("button", { name: /Marcar todas como leídas/ }).click();
    await expect(page.getByRole("button", { name: /Marcar todas como leídas/ })).toBeDisabled();
    await expect(campana).toHaveAttribute("aria-label", "Notificaciones");
  });

  test("el gerente asigna un mecánico y el estatus cambia a Asignado", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/reportes");
    const fila = page.getByRole("row", { name: new RegExp(ubicacion) });
    await fila.getByRole("link", { name: /Ver|Editar/ }).click();

    const mecanico = page.locator("#assign_mechanic option", { hasText: "M1" });
    await page.locator("#assign_mechanic").selectOption((await mecanico.getAttribute("value")) as string);
    await page.getByRole("button", { name: /Asignar/ }).click();
    await expect(page.getByRole("row", { name: /^Estatus Asignado/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /M1 Prueba E2E \(M1\)/ })).toBeVisible();
  });

  test("el mecánico ve el reporte entre los suyos y el operador, el nuevo estatus", async ({ page }) => {
    await loginOk(page, "M1");
    await page.goto("/reportes");
    await expect(page.getByRole("heading", { name: "Reportes asignados a mí" })).toBeVisible();
    await expect(page.getByRole("row", { name: new RegExp(ubicacion) })).toContainText("Asignado");
  });
});
