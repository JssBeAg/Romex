"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import ReportForm from "@/components/ReportForm";
import { OPERATOR_ROLE } from "@/lib/roles";
import { createReport } from "@/lib/reports";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [OPERATOR_ROLE];

export default function NewReportPage() {
  const router = useRouter();
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nuevo reporte de falla</h1>
        <p role="alert">Solo los operadores pueden crear reportes.</p>
        <p>
          <Link className="back-link" href="/reportes">Volver a la lista</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nuevo reporte de falla</h1>
      <p>
        <Link className="back-link" href="/reportes">Volver a la lista</Link>
      </p>
      <ReportForm
        onSubmit={createReport}
        onSaved={() => router.push("/reportes")}
        onCancel={() => router.push("/reportes")}
      />
    </main>
  );
}
