import { expect, test } from "@playwright/test";
import { formError, loginOk } from "./helpers";

// México +52 queda elegido de verdad (no solo mostrado) y el domicilio lleva colonia y calle como texto.
test.describe("Alta de trabajador: código por defecto y domicilio", () => {
  test("con el +52 por defecto y colonia y calle escritas, el alta se guarda", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores/nuevo");
    await expect(page.locator("#phone_code_id")).toHaveValue(/\d+/);
    await expect(page.locator("#phone_code_id option:checked")).toContainText("+52");

    const id = `E${Date.now().toString().slice(-7)}`;
    await page.locator("#enrollment_id").fill(id);
    await page.getByLabel("Nombre(s)").fill("Lucía");
    await page.getByLabel("Apellido paterno").fill("Prueba");
    await page.getByLabel("Apellido materno").fill("Domicilio");
    await page.locator("#email").fill(`${id.toLowerCase()}@example.com`);
    await page.locator("#phone_number").fill("8441234567"); // el código NO se toca
    await page.locator("#sex_id").selectOption({ index: 1 });
    await page.locator("#role_id").selectOption({ index: 1 });
    await expect(page.locator("#address_country")).toHaveValue("México");
    await expect(page.locator("#address_state option")).not.toHaveCount(1);
    await page.locator("#address_state").selectOption({ label: "Coahuila de Zaragoza" });
    await expect(page.locator("#address_municipality option")).not.toHaveCount(1);
    await page.locator("#address_municipality").selectOption({ label: "Saltillo" });
    await page.locator("#address_neighborhood").fill("Colonia que no está en ningún catálogo");
    await page.locator("#address_street").fill("Calle Inventada");
    await page.locator("#exterior_number").fill("12-A");
    await page.locator("#password").fill("Clave12345x");
    await page.locator("#password_confirmation").fill("Clave12345x");
    await page.getByRole("button", { name: "Guardar" }).click();

    await expect(page).toHaveURL(/\/trabajadores$/);
    await expect(formError(page)).toHaveCount(0);
    // La lista es paginada: se busca por matrícula y se abre para comprobar lo guardado
    await page.getByLabel("Buscar (matrícula o nombre)").fill(id);
    await page.getByRole("button", { name: "Buscar" }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.locator("tbody tr")).toContainText(id);
    await page.getByRole("link", { name: "Editar" }).click();
    await expect(page.locator("#address_neighborhood")).toHaveValue("Colonia que no está en ningún catálogo");
    await expect(page.locator("#address_street")).toHaveValue("Calle Inventada");
    await expect(page.locator("#exterior_number")).toHaveValue("12-A");
    await expect(page.locator("#address_municipality option:checked")).toHaveText("Saltillo");
    await expect(page.locator("#phone_code_id option:checked")).toContainText("+52");
  });
});
