"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import UnitForm from "@/components/UnitForm";
import { useManagerGuard } from "@/lib/useManagerGuard";
import { createUnit } from "@/lib/units";

export default function NewUnitPage() {
  const router = useRouter();
  const { loading, allowed } = useManagerGuard();

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nueva unidad</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nueva unidad</h1>
      <p>
        <Link className="back-link" href="/unidades">Volver a la lista</Link>
      </p>
      <UnitForm
        onSubmit={createUnit}
        onSaved={() => router.push("/unidades")}
        onCancel={() => router.push("/unidades")}
      />
    </main>
  );
}
