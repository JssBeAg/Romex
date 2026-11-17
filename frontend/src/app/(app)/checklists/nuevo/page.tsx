"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import ChecklistForm from "@/components/ChecklistForm";
import { OPERATOR_ROLE } from "@/lib/roles";
import { createChecklist } from "@/lib/checklists";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [OPERATOR_ROLE];

export default function NewChecklistPage() {
  const router = useRouter();
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nuevo checklist</h1>
        <p role="alert">Solo los operadores pueden crear checklists.</p>
        <p>
          <Link className="back-link" href="/checklists">Volver a la lista</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nuevo checklist</h1>
      <p>
        <Link className="back-link" href="/checklists">Volver a la lista</Link>
      </p>
      <ChecklistForm
        onSubmit={createChecklist}
        onSaved={() => router.push("/checklists")}
        onCancel={() => router.push("/checklists")}
      />
    </main>
  );
}
