"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import PlanForm from "@/components/PlanForm";
import { MANAGER_ROLE } from "@/lib/roles";
import { createPlan } from "@/lib/preventive";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

export default function NewPlanPage() {
  const router = useRouter();
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nuevo plan</h1>
        <p role="alert">Solo los gerentes pueden administrar los planes.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nuevo plan preventivo</h1>
      <p>
        <Link className="back-link" href="/preventivo/planes">Volver a la lista</Link>
      </p>
      <PlanForm
        onSubmit={createPlan}
        onSaved={() => router.push("/preventivo/planes")}
        onCancel={() => router.push("/preventivo/planes")}
      />
    </main>
  );
}
