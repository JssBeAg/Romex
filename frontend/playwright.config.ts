import { defineConfig, devices } from "@playwright/test";

// Pruebas de navegador contra el sistema ya levantado (interfaz en :3000 y API en :8000).
// Antes de correrlas: python manage.py seed_e2e  (ver docs/pruebas.md)
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1, // comparten la misma base de datos
  retries: process.env.CI ? 1 : 0,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    locale: "es-MX",
    timezoneId: "America/Mexico_City",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // En el entorno de desarrollo se puede apuntar a un Chromium ya instalado
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
