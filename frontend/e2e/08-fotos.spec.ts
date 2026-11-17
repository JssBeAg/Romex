import { expect, test } from "@playwright/test";
import { loginOk } from "./helpers";

// Un PNG válido de 1×1 píxel (el servidor lo recorta y lo agranda a 512×512)
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
  "base64"
);

// La fotografía de un trabajador es opcional; sin ella se ven sus iniciales.
test.describe.serial("Fotografía de los trabajadores", () => {
  const filaO2 = (page: import("@playwright/test").Page) => page.getByRole("row", { name: /^O2 O2 Prueba/ });

  test("sin fotografía se ven las iniciales, también en el encabezado", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores");
    const fila = filaO2(page);
    await expect(fila.locator(".avatar-initials")).toHaveText("OP");
    await expect(fila.locator(".avatar img")).toHaveCount(0);
    // La primera letra del nombre y del apellido paterno; decorativo (el nombre ya está escrito al lado)
    await expect(fila.locator(".avatar")).toHaveAttribute("aria-hidden", "true");
    await expect(page.locator("header .avatar-initials").first()).toHaveText("GP");
  });

  test("un archivo que no es imagen se rechaza antes de enviar", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores");
    await filaO2(page).getByRole("link", { name: "Editar" }).click();
    await expect(page.getByRole("img", { name: /Sin fotografía: se mostrarán las iniciales de O2 Prueba/ })).toBeVisible();

    await page.locator("#photo").setInputFiles({ name: "nota.txt", mimeType: "text/plain", buffer: Buffer.from("hola") });
    await expect(page.locator(".field-error", { hasText: "JPG, PNG o WebP" })).toBeVisible();

    await page.locator("#photo").setInputFiles({
      name: "pesada.png", mimeType: "image/png", buffer: Buffer.alloc(5 * 1024 * 1024 + 1024),
    });
    await expect(page.locator(".field-error", { hasText: "5 MB" })).toBeVisible();
  });

  test("el gerente sube una fotografía y se ve en la lista", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores");
    await filaO2(page).getByRole("link", { name: "Editar" }).click();

    await page.locator("#photo").setInputFiles({ name: "foto.png", mimeType: "image/png", buffer: PNG });
    // Vista previa antes de guardar
    await expect(page.locator(".photo-field .avatar img")).toBeVisible();
    await expect(page.getByRole("img", { name: "Fotografía de O2 Prueba" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Quitar fotografía" })).toBeVisible();

    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/trabajadores$/);
    await expect(filaO2(page).locator(".avatar img")).toBeVisible();
    await expect(filaO2(page).locator(".avatar-initials")).toHaveCount(0);
  });

  test("la persona ve su propia fotografía en el encabezado y nadie más puede pedirla", async ({ page, browser }) => {
    // El gerente ve el id de O2
    await loginOk(page, "G1");
    const lista = await (await page.request.get("http://localhost:8000/api/trabajadores/?page_size=100")).json();
    const o2 = lista.workers.find((w: { enrollment_id: string }) => w.enrollment_id === "O2");
    expect(o2.photo_url).toMatch(/^trabajadores\/\d+\/foto\/\?v=[0-9a-f]{32}$/);
    const urlFoto = `http://localhost:8000/api/${o2.photo_url}`;
    const comoGerente = await page.request.get(urlFoto);
    expect(comoGerente.status()).toBe(200);
    expect(comoGerente.headers()["content-type"]).toBe("image/jpeg");

    // O2 la ve en su encabezado
    const contextoO2 = await browser.newContext();
    const paginaO2 = await contextoO2.newPage();
    await loginOk(paginaO2, "O2");
    await expect(paginaO2.locator("header .avatar img").first()).toBeVisible();
    expect((await paginaO2.request.get(urlFoto)).status()).toBe(200);
    await contextoO2.close();

    // Otro operador no puede pedirla
    const contextoO1 = await browser.newContext();
    const paginaO1 = await contextoO1.newPage();
    await loginOk(paginaO1, "O1");
    expect((await paginaO1.request.get(urlFoto)).status()).toBe(403);
    // ni cambiarla
    expect((await paginaO1.request.delete(urlFoto.split("?")[0])).status()).toBe(403);
    await contextoO1.close();

    // Sin sesión tampoco
    const anonimo = await browser.newContext();
    expect((await anonimo.request.get(urlFoto)).status()).toBe(401);
    await anonimo.close();
  });

  test("el gerente la quita y vuelven las iniciales", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores");
    await filaO2(page).getByRole("link", { name: "Editar" }).click();
    await expect(page.locator(".photo-field .avatar img")).toBeVisible();

    await page.getByRole("button", { name: "Quitar fotografía" }).click();
    // Ya muestra las iniciales y el botón desaparece
    await expect(page.locator(".photo-field .avatar-initials")).toHaveText("OP");
    await expect(page.getByRole("button", { name: "Quitar fotografía" })).toHaveCount(0);

    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/trabajadores$/);
    await expect(filaO2(page).locator(".avatar-initials")).toHaveText("OP");
    await expect(filaO2(page).locator(".avatar img")).toHaveCount(0);
  });

  test("en un trabajador nuevo, las iniciales siguen lo que se escribe", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores/nuevo");
    await expect(page.locator(".photo-field .avatar-initials")).toHaveText("?");
    await page.getByLabel("Nombre(s)").fill("ana maría");
    await page.getByLabel("Apellido paterno").fill("zúñiga");
    await expect(page.locator(".photo-field .avatar-initials")).toHaveText("AZ");
  });
});
