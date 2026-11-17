import { expect, test, type Page } from "@playwright/test";
import { loginOk } from "./helpers";

// Un PNG válido de 1×1 píxel (el servidor lo guarda como JPG)
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
  "base64"
);

// La fotografía de una refacción es opcional; sin ella se ve un ícono neutro.
test.describe.serial("Fotografía de las refacciones", () => {
  const NOMBRE = "Refacción con foto E2E";
  const fila = (page: Page) => page.getByRole("row", { name: new RegExp(NOMBRE) });

  async function buscar(page: Page) {
    await page.goto("/refacciones");
    await page.getByLabel("Mostrar").selectOption("all");
    await page.getByLabel(/Buscar/).fill(NOMBRE);
    await page.getByRole("button", { name: "Buscar" }).click();
  }

  test("una refacción nueva sin foto muestra el ícono, y un archivo inválido se rechaza", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/refacciones/nueva");
    await expect(page.getByRole("img", { name: /Sin fotografía de la refacción/ })).toBeVisible();

    await page.locator("#photo").setInputFiles({ name: "nota.txt", mimeType: "text/plain", buffer: Buffer.from("hola") });
    await expect(page.locator(".field-error", { hasText: "JPG, PNG o WebP" })).toBeVisible();
    await page.locator("#photo").setInputFiles({
      name: "pesada.png", mimeType: "image/png", buffer: Buffer.alloc(5 * 1024 * 1024 + 1024),
    });
    await expect(page.locator(".field-error", { hasText: "5 MB" })).toBeVisible();
  });

  test("se crea con foto, con vista previa, y se ve en la lista", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/refacciones/nueva");
    await page.getByLabel("Nombre", { exact: true }).fill(NOMBRE);
    await page.locator("#photo").setInputFiles({ name: "pieza.png", mimeType: "image/png", buffer: PNG });
    await expect(page.locator(".photo-field .part-photo img")).toBeVisible();
    await expect(page.getByRole("button", { name: "Quitar fotografía" })).toBeVisible();
    await page.getByRole("button", { name: "Guardar" }).click();

    await expect(page).toHaveURL(/\/refacciones$/);
    await buscar(page);
    await expect(fila(page).locator(".part-photo img")).toBeVisible();
  });

  test("al editar se ve la foto guardada y se puede quitar", async ({ page }) => {
    await loginOk(page, "G1");
    await buscar(page);
    await fila(page).getByRole("link", { name: "Ver / Editar" }).click();
    await expect(page.getByRole("img", { name: `Fotografía de ${NOMBRE}` })).toBeVisible();

    await page.getByRole("button", { name: "Quitar fotografía" }).click();
    await expect(page.getByRole("img", { name: /Sin fotografía de/ })).toBeVisible();
    await page.getByRole("button", { name: "Guardar" }).first().click();
    await expect(page.getByText("Se guardaron los cambios.")).toBeVisible();
    await expect(page.getByRole("img", { name: /Sin fotografía de/ })).toBeVisible();

    await buscar(page);
    await expect(fila(page).locator(".part-photo img")).toHaveCount(0);
  });

  test("sin sesión nadie puede pedir la foto", async ({ page, browser }) => {
    await loginOk(page, "G1");
    const lista = await (await page.request.get("http://localhost:8000/api/refacciones/?q=Filtro&page_size=5")).json();
    const id = lista.spare_parts[0].id;
    // Sin sesión
    const anon = await browser.newContext();
    expect((await anon.request.get(`http://localhost:8000/api/refacciones/${id}/foto/`)).status()).toBe(401);
    await anon.close();
  });

  test("limpieza: se elimina la refacción de prueba", async ({ page }) => {
    await loginOk(page, "G1");
    await buscar(page);
    page.once("dialog", (dialog) => dialog.accept());
    await fila(page).getByRole("button", { name: "Eliminar" }).click();
    await expect(page.getByText(`Se eliminó: ${NOMBRE}.`)).toBeVisible();
  });
});
