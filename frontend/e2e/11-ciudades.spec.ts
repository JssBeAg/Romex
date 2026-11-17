import { expect, test } from "@playwright/test";
import { loginOk } from "./helpers";

// Estados y municipios salen del servicio del INEGI (en las pruebas, un INEGI de mentira local).
test.describe("Estados y municipios del INEGI", () => {
  test.beforeEach(async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores/nuevo");
    await expect(page.locator("#address_country")).toHaveValue("México");
    await expect(page.locator("#address_state option")).not.toHaveCount(1);
  });

  const municipios = (page: import("@playwright/test").Page) => page.locator("#address_municipality option");

  test("ofrece los 32 estados y cambiar de estado reemplaza los municipios", async ({ page }) => {
    // 32 estados + la opción vacía
    await expect(page.locator("#address_state option")).toHaveCount(33);
    await page.locator("#address_state").selectOption({ label: "Jalisco" });
    await expect(municipios(page).filter({ hasText: "Guadalajara" })).toHaveCount(1);
    await expect(municipios(page).filter({ hasText: "Zapopan" })).toHaveCount(1);

    await page.locator("#address_state").selectOption({ label: "Nuevo León" });
    await expect(municipios(page).filter({ hasText: "Monterrey" })).toHaveCount(1);
    await expect(municipios(page).filter({ hasText: "Guadalajara" })).toHaveCount(0);
  });

  test("los municipios de Coahuila siguen y colonia y calle son texto libre", async ({ page }) => {
    await page.locator("#address_state").selectOption({ label: "Coahuila de Zaragoza" });
    await expect(municipios(page).filter({ hasText: "Saltillo" })).toHaveCount(1);
    await page.locator("#address_municipality").selectOption({ label: "Saltillo" });
    await expect(page.locator("input#address_neighborhood")).toBeVisible();
    await expect(page.locator("input#address_street")).toBeVisible();
    await expect(page.locator("select#address_neighborhood")).toHaveCount(0);
  });

  test("la placa de una unidad también elige el estado del INEGI", async ({ page }) => {
    await page.goto("/unidades/nueva");
    await expect(page.locator("#plate_state option")).toHaveCount(33);
  });
});
