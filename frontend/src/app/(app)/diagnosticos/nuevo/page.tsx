"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import DiagnosisForm from "@/components/DiagnosisForm";
import { createDiagnosis } from "@/lib/diagnoses";
import { MECHANIC_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MECHANIC_ROLE];

export default function NewDiagnosisPage() {
  const router = useRouter();
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nuevo diagnóstico</h1>
        <p role="alert">Solo los mecánicos pueden registrar diagnósticos.</p>
        <p>
          <Link className="back-link" href="/diagnosticos">Volver a la lista</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nuevo diagnóstico</h1>
      <p>
        <Link className="back-link" href="/diagnosticos">Volver a la lista</Link>
      </p>
      <DiagnosisForm
        onSubmit={createDiagnosis}
        onSaved={() => router.push("/diagnosticos")}
        onCancel={() => router.push("/diagnosticos")}
      />
    </main>
  );
}
