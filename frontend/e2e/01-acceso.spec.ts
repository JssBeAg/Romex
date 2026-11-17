import { expect, test } from "@playwright/test";
import { formError, login, loginOk } from "./helpers";

test.describe("Acceso", () => {
  test("con contraseña incorrecta muestra un error y no entra", async ({ page }) => {
    await login(page, "O1", "incorrecta");
    await expect(formError(page)).toHaveText("Matrícula o contraseña incorrectas");
    await expect(page).toHaveURL(/\/login/);
  });

  test("con datos correctos entra, y al cerrar sesión vuelve al acceso", async ({ page }) => {
    await loginOk(page, "O1");
    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page).toHaveURL(/\/login/);
    // Ya sin sesión, una pantalla interna lo regresa al acceso
    await page.goto("/reportes");
    await expect(page).toHaveURL(/\/login/);
  });

  test("sin sesión no se puede ver ninguna pantalla interna", async ({ page }) => {
    for (const path of ["/", "/dashboard", "/refacciones", "/trabajadores", "/notificaciones"]) {
      await page.goto(path);
      await expect(page, path).toHaveURL(/\/login/);
    }
  });

  test("puede mostrar y ocultar la contraseña", async ({ page }) => {
    await page.goto("/login");
    const field = page.getByLabel("Contraseña", { exact: true });
    await expect(field).toHaveAttribute("type", "password");
    await page.getByRole("button", { name: /Mostrar contraseña/i }).click();
    await expect(field).toHaveAttribute("type", "text");
  });

  test("cada rol ve su menú", async ({ page }) => {
    await loginOk(page, "G1");
    const menu = page.getByRole("navigation", { name: "Menú principal" });
    for (const item of ["Dashboard", "Trabajadores", "Unidades", "Refacciones", "Bitácora"]) {
      await expect(menu.getByRole("link", { name: item })).toBeVisible();
    }
    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page).toHaveURL(/\/login/);

    await loginOk(page, "O1");
    await expect(menu.getByRole("link", { name: "Dashboard" })).toHaveCount(0);
    await expect(menu.getByRole("link", { name: "Trabajadores" })).toHaveCount(0);
    await expect(menu.getByRole("link", { name: "Bitácora" })).toHaveCount(0);
  });

  test("un operador no entra a las pantallas del gerente", async ({ page }) => {
    await loginOk(page, "O1");
    for (const path of ["/dashboard", "/trabajadores", "/bitacora", "/refacciones"]) {
      await page.goto(path);
      await expect(page.getByText("No tienes acceso a esta sección."), path).toBeVisible();
    }
  });
});
