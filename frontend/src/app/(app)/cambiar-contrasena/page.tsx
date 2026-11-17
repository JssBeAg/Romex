"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getCurrentUser, type User } from "@/lib/api";
import { changePassword, type PasswordInput, validatePasswordChange } from "@/lib/account";
import type { FieldErrors } from "@/lib/http";
import { useFormFeedback } from "@/lib/useFormFeedback";

const LABELS: Record<string, string> = {
  current_password: "Contraseña actual",
  new_password: "Contraseña nueva",
  confirm_password: "Confirmación",
};

export default function ChangePasswordPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    getCurrentUser().then((u) => {
      if (!u) router.replace("/login");
      else setUser(u);
    });
  }, [router]);

  const input: PasswordInput = {
    current_password: current,
    new_password: next,
    confirm_password: confirm,
  };
  const localErrors: FieldErrors =
    confirm !== "" && next !== confirm
      ? { confirm_password: ["La confirmación no coincide con la contraseña nueva."] }
      : {};
  const feedback = useFormFeedback({
    payload: input,
    validate: validatePasswordChange,
    localErrors,
    labels: LABELS,
  });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const res = await changePassword(input);
    setSubmitting(false);
    if (res.ok) {
      setDone(true);
      // A forced change leads to the home page; a voluntary one stays here with a notice
      // (a full load, so the menu forgets that the change was pending)
      if (user?.must_change_password) window.location.assign("/");
      else {
        setCurrent("");
        setNext("");
        setConfirm("");
      }
      return;
    }
    feedback.rejectResult(res);
  }

  if (!user) return <main><p>Cargando…</p></main>;
  const forced = user.must_change_password && !done;

  return (
    <main>
      <h1>Cambiar contraseña</h1>
      {forced ? (
        <p role="status">
          Por seguridad debes elegir una contraseña nueva antes de usar el sistema.
        </p>
      ) : (
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      )}
      {done && !user.must_change_password && <p role="status">Tu contraseña se cambió correctamente.</p>}

      <form method="post" onSubmit={handleSubmit} {...feedback.formProps}>
        <fieldset>
          <legend>Tu contraseña</legend>
          <p>
            <label htmlFor="current_password">Contraseña actual</label>
            <br />
            <input id="current_password" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
            {feedback.fieldErrors("current_password")}
          </p>
          <p>
            <label htmlFor="new_password">Contraseña nueva</label>
            <br />
            <input id="new_password" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} required />
            <span className="hint"> Mínimo 8 caracteres, no solo números, no muy común y distinta de tu matrícula.</span>
            {feedback.fieldErrors("new_password")}
          </p>
          <p>
            <label htmlFor="confirm_password">Confirma la contraseña nueva</label>
            <br />
            <input id="confirm_password" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
            {feedback.fieldErrors("confirm_password")}
          </p>
        </fieldset>
        <p>
          <button type="submit" disabled={submitting}>{submitting ? "Guardando…" : "Cambiar contraseña"}</button>
        </p>
      </form>
      {feedback.dialog}
    </main>
  );
}
