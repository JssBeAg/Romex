import { expect, test, type Page } from "@playwright/test";
import { loginOk } from "./helpers";

// Código del país + número, y otras formas de localizar a la MISMA persona ("Número 2"...).
test.describe.serial("Teléfono con código y contactos del trabajador", () => {
  const filaO2 = (page: Page) => page.getByRole("row", { name: /^O2 O2 Prueba/ });

  async function editarO2(page: Page) {
    await loginOk(page, "G1");
    await page.goto("/trabajadores");
    await filaO2(page).getByRole("link", { name: "Editar" }).click();
    await expect(page.locator("#phone_number")).toBeVisible();
  }

  test("el teléfono principal lleva su código y se ve completo en la lista", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/trabajadores");
    await expect(filaO2(page)).toContainText("+52 8441234567");
    await filaO2(page).getByRole("link", { name: "Editar" }).click();
    await expect(page.locator("#phone_code_id")).toHaveValue(/\d+/);
    await expect(page.locator("#phone_code_id option:checked")).toHaveText("México (+52)");
  });

  test("el código y el número tienen cada uno su etiqueta y el número no se encoge", async ({ page }) => {
    await editarO2(page);
    // Cada campo con su propio nombre: el código no se llama "número"
    await expect(page.getByLabel("Código del país")).toBeVisible();
    await expect(page.getByLabel("Número telefónico")).toBeVisible();
    const numero = await page.locator("#phone_number").boundingBox();
    expect(numero!.width).toBeGreaterThan(220);
    // Lo mismo en un contacto adicional
    await page.getByRole("button", { name: "Agregar teléfono" }).click();
    const fila = page.getByRole("group", { name: "Contacto adicional 1" });
    await expect(fila.getByLabel("Código del país")).toBeVisible();
    await expect(fila.getByLabel("Número telefónico")).toBeVisible();
    const extra = await fila.getByLabel("Número telefónico").boundingBox();
    expect(extra!.width).toBeGreaterThan(160);
  });

  test("el número principal solo acepta dígitos", async ({ page }) => {
    await editarO2(page);
    await page.locator("#phone_number").fill("84a");
    await expect(page.locator(".field-error", { hasText: "solo números" })).toBeVisible();
    await page.locator("#phone_number").fill("8441234567");
    await expect(page.locator(".field-error", { hasText: "solo números" })).toHaveCount(0);
  });

  test("agrega un 'Número 2' con el nombre de la persona y se ve en la lista", async ({ page }) => {
    await editarO2(page);
    await expect(page.getByText("No tiene contactos adicionales.")).toBeVisible();
    await page.getByRole("button", { name: "Agregar teléfono" }).click();

    const fila = page.getByRole("group", { name: "Contacto adicional 1" });
    // El código del contacto empieza igual que el principal; la etiqueta sugiere "Número 2"
    await expect(fila.getByLabel("Etiqueta")).toHaveAttribute("placeholder", "Número 2");
    await fila.getByPlaceholder("Solo números").fill("8449990000");
    await fila.getByLabel("De quién es (opcional)").fill("Ana (esposa)");

    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/trabajadores$/);
    const lista = filaO2(page);
    await expect(lista).toContainText("+52 8441234567");
    await expect(lista).toContainText("Número 2:");
    await expect(lista).toContainText("+52 8449990000");
    await expect(lista).toContainText("(Ana (esposa))");
  });

  test("un contacto con datos mal escritos se avisa antes de guardar", async ({ page }) => {
    await editarO2(page);
    // Se conserva el contacto guardado
    await expect(page.getByRole("group", { name: "Contacto adicional 1" })).toBeVisible();
    await page.getByRole("button", { name: "Agregar correo" }).click();
    const fila = page.getByRole("group", { name: "Contacto adicional 2" });
    await fila.locator("input[type='email']").fill("no-es-correo");
    await expect(page.locator(".field-error", { hasText: "el correo no es válido" })).toBeVisible();
    // Repetir el principal tampoco se permite
    await page.getByRole("group", { name: "Contacto adicional 1" }).getByPlaceholder("Solo números").fill("8441234567");
    await expect(page.locator(".field-error", { hasText: "repite el teléfono principal" })).toBeVisible();
  });

  test("no deja pasar del máximo de contactos", async ({ page }) => {
    await editarO2(page);
    await page.getByRole("button", { name: "Agregar teléfono" }).click();
    await page.getByRole("button", { name: "Agregar correo" }).click();
    await expect(page.getByRole("group", { name: /Contacto adicional/ })).toHaveCount(3);
    await expect(page.getByRole("button", { name: "Agregar teléfono" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Agregar correo" })).toBeDisabled();
    await expect(page.getByText("Llegaste al máximo de 3 contactos.")).toBeVisible();
    // Al quitar uno se puede agregar otro
    await page.getByRole("button", { name: "Quitar contacto adicional 3" }).click();
    await expect(page.getByRole("button", { name: "Agregar teléfono" })).toBeEnabled();
  });

  test("quitar el contacto lo borra al guardar (y deja todo como estaba)", async ({ page }) => {
    await editarO2(page);
    await page.getByRole("button", { name: "Quitar contacto adicional 1" }).click();
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page).toHaveURL(/\/trabajadores$/);
    await expect(filaO2(page)).not.toContainText("Número 2:");
    await expect(filaO2(page)).toContainText("+52 8441234567");
  });
});
