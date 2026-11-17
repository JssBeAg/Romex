"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import MaintenanceForm from "@/components/MaintenanceForm";
import { createMaintenance } from "@/lib/maintenances";
import { MECHANIC_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MECHANIC_ROLE];

export default function NewMaintenancePage() {
  const router = useRouter();
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nuevo mantenimiento</h1>
        <p role="alert">Solo los mecánicos pueden registrar mantenimientos.</p>
        <p>
          <Link className="back-link" href="/mantenimientos">Volver a la lista</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nuevo mantenimiento</h1>
      <p>
        <Link className="back-link" href="/mantenimientos">Volver a la lista</Link>
      </p>
      <MaintenanceForm
        onSubmit={createMaintenance}
        onSaved={() => router.push("/mantenimientos")}
        onCancel={() => router.push("/mantenimientos")}
      />
    </main>
  );
}
