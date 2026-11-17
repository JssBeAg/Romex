import { expect, test } from "@playwright/test";
import { formError, login } from "./helpers";

// Usa la cuenta L1, que solo sirve para esta prueba (se restablece con seed_e2e).
test("5 intentos fallidos bloquean la cuenta, aun con la contraseña correcta", async ({ page }) => {
  for (let i = 0; i < 5; i++) {
    await login(page, "L1", "incorrecta");
    await expect(formError(page)).toHaveText("Matrícula o contraseña incorrectas");
  }
  await login(page, "L1"); // contraseña correcta
  await expect(formError(page)).toContainText(/bloquead/i);
  await expect(page).toHaveURL(/\/login/);
});
