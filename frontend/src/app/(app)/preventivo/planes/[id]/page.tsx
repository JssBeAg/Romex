"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import PlanForm from "@/components/PlanForm";
import { MANAGER_ROLE } from "@/lib/roles";
import { type Plan, getPlan, updatePlan } from "@/lib/preventive";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

export default function PlanPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getPlan(id).then((res) => {
      if (res.ok && res.data) setPlan(res.data.plan);
      else setLoadError(res.error ?? "No se pudo cargar el plan");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Plan preventivo</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>{plan?.name ?? "Plan preventivo"}</h1>
      <p>
        <Link className="back-link" href="/preventivo/planes">Volver a la lista</Link>
      </p>
      {loadError && <p role="alert">{loadError}</p>}
      {!plan && !loadError && <p>Cargando...</p>}
      {plan && (
        <PlanForm
          plan={plan}
          onSubmit={(input) => updatePlan(id, input)}
          onSaved={() => router.push("/preventivo/planes")}
          onCancel={() => router.push("/preventivo/planes")}
        />
      )}
    </main>
  );
}
