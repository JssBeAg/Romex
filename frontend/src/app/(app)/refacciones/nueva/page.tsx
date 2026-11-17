"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import SparePartForm from "@/components/SparePartForm";
import { MANAGER_ROLE } from "@/lib/roles";
import { createSparePart } from "@/lib/spareParts";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

export default function NewSparePartPage() {
  const router = useRouter();
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nueva refacción</h1>
        <p role="alert">Solo los gerentes pueden administrar las refacciones.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nueva refacción</h1>
      <p>
        <Link className="back-link" href="/refacciones">Volver a la lista</Link>
      </p>
      <SparePartForm
        onSubmit={createSparePart}
        onSaved={() => router.push("/refacciones")}
        onCancel={() => router.push("/refacciones")}
      />
    </main>
  );
}
