"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, login } from "@/lib/api";
import { useTheme } from "@/lib/theme";
import styles from "./login.module.css";

// Sun (shown in dark mode, click for light) and moon (shown in light mode)
function ThemeIcon({ dark }: { dark: boolean }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {dark ? (
        <>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </>
      ) : (
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
      )}
    </svg>
  );
}

// Eye icon; a slash across it means "click to hide"
function EyeIcon({ crossed }: { crossed: boolean }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
      <circle cx="12" cy="12" r="3" />
      {crossed && <line x1="3" y1="3" x2="21" y2="21" />}
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [enrollmentId, setEnrollmentId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { theme, toggleTheme } = useTheme();

  // If there is already a session, skip the login screen
  useEffect(() => {
    getCurrentUser().then((user) => {
      if (user) router.replace("/");
    });
  }, [router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    const result = await login(enrollmentId, password);

    setSubmitting(false);
    if (result.error) {
      setError(result.error);
      return;
    }
    router.replace(result.user?.must_change_password ? "/cambiar-contrasena" : "/");
  }

  return (
    <div className={styles.page}>
      {theme && (
        <button
          className={styles.themeToggle}
          type="button"
          onClick={toggleTheme}
          aria-label={
            theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"
          }
        >
          <ThemeIcon dark={theme === "dark"} />
        </button>
      )}

      <main className={styles.card}>
        {/* Two logo versions: the CSS shows the one that fits the current theme */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className={`${styles.logo} ${styles.logoLight}`}
          src="/romex-logo.png"
          alt="ROMEX Logística"
          width={270}
          height={73}
        />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className={`${styles.logo} ${styles.logoDark}`}
          src="/romex-logo-dark.png"
          alt="ROMEX Logística"
          width={270}
          height={73}
        />
        <h1 className={styles.title}>Iniciar sesión</h1>

        <form method="post" onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="enrollment_id">
              Matrícula
            </label>
            <input
              className={styles.input}
              id="enrollment_id"
              type="text"
              value={enrollmentId}
              onChange={(e) => setEnrollmentId(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="password">
              Contraseña
            </label>
            <div className={styles.passwordWrap}>
              <input
                className={styles.input}
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                className={styles.toggle}
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
                aria-pressed={showPassword}
              >
                <EyeIcon crossed={showPassword} />
              </button>
            </div>
          </div>

          <button className={styles.button} type="submit" disabled={submitting}>
            {submitting ? "Ingresando..." : "Ingresar"}
          </button>

          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
        </form>
      </main>
    </div>
  );
}
