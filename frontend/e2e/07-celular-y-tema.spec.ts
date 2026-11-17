import { expect, test, type Page } from "@playwright/test";
import { login, loginOk } from "./helpers";

async function sinDesbordeHorizontal(page: Page, ruta: string) {
  await page.goto(ruta);
  await page.waitForLoadState("networkidle");
  const { scroll, ancho } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    ancho: document.documentElement.clientWidth,
  }));
  expect(scroll, `${ruta}: la página se desborda a lo ancho (${scroll} > ${ancho})`).toBeLessThanOrEqual(ancho);
}

test.describe("Celular (375 px)", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("el acceso cabe en la pantalla", async ({ page }) => {
    await sinDesbordeHorizontal(page, "/login");
  });

  test("las pantallas del gerente caben en la pantalla", async ({ page }) => {
    await loginOk(page, "G1");
    for (const ruta of ["/", "/dashboard", "/reportes", "/refacciones", "/unidades", "/trabajadores", "/trabajadores/nuevo", "/preventivo", "/notificaciones", "/bitacora"]) {
      await sinDesbordeHorizontal(page, ruta);
    }
  });

  test("las pantallas del operador caben en la pantalla", async ({ page }) => {
    await loginOk(page, "O1");
    for (const ruta of ["/", "/reportes", "/reportes/nuevo", "/checklists", "/cambiar-contrasena"]) {
      await sinDesbordeHorizontal(page, ruta);
    }
  });

  test("todo el contenido de cada tabla se puede alcanzar (cabe o se desplaza dentro de su caja)", async ({ page }) => {
    await loginOk(page, "G1");
    const pantallas = ["/reportes", "/unidades", "/trabajadores", "/mantenimientos", "/diagnosticos", "/checklists",
      "/kardex", "/refacciones", "/preventivo", "/preventivo/planes", "/bitacora"];
    for (const ruta of pantallas) {
      await page.goto(ruta);
      await page.waitForLoadState("networkidle");
      const tablas = await page.locator("table").evaluateAll((lista) =>
        lista.map((t) => {
          const caja = t.closest(".table-scroll") as HTMLElement | null;
          const cabe = t.getBoundingClientRect().right <= window.innerWidth + 1;
          const seDesplaza = !!caja && ["auto", "scroll"].includes(getComputedStyle(caja).overflowX);
          return { cabe, seDesplaza };
        })
      );
      expect(tablas.length, `${ruta}: no se encontró ninguna tabla`).toBeGreaterThan(0);
      for (const t of tablas) {
        expect(t.cabe || t.seDesplaza, `${ruta}: una tabla queda recortada en el celular`).toBe(true);
      }
    }
  });

  test("los botones de acción de una lista ancha se alcanzan desplazando", async ({ page }) => {
    await loginOk(page, "G1");
    await page.goto("/reportes");
    const enlace = page.locator("tbody a", { hasText: /^(Ver|Editar)$/ }).first();
    await enlace.scrollIntoViewIfNeeded();
    const caja = await enlace.boundingBox();
    expect(caja!.x + caja!.width).toBeLessThanOrEqual(375 + 1);
    await enlace.click();
    await expect(page).toHaveURL(/\/reportes\/\d+/);
  });
});

test.describe("Modo oscuro", () => {
  test("se activa, se recuerda al recargar y no rompe pantallas", async ({ page }) => {
    await loginOk(page, "G1");
    await page.getByRole("button", { name: "Cambiar a modo oscuro" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(page.getByRole("button", { name: "Cambiar a modo claro" })).toBeVisible();

    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    // El texto no queda del mismo color que el fondo
    for (const ruta of ["/dashboard", "/refacciones"]) {
      await page.goto(ruta);
      const { fondo, texto } = await page.evaluate(() => {
        const cuerpo = getComputedStyle(document.body);
        return { fondo: cuerpo.backgroundColor, texto: cuerpo.color };
      });
      expect(fondo, ruta).not.toBe(texto);
    }

    // Se vuelve al modo claro y se deja como estaba
    await page.getByRole("button", { name: "Cambiar a modo claro" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  });

  test("también se puede cambiar desde el acceso", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /Cambiar a modo (oscuro|claro)/ }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", /dark|light/);
    await login(page, "O1");
    await expect(page).toHaveURL(/\/$/);
  });
});
