"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import UnitForm from "@/components/UnitForm";
import { useManagerGuard } from "@/lib/useManagerGuard";
import { type Unit, getUnit, updateUnit } from "@/lib/units";

export default function EditUnitPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useManagerGuard();
  const [unit, setUnit] = useState<Unit | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getUnit(id).then((res) => {
      if (res.ok && res.data) setUnit(res.data.unit);
      else setLoadError(res.error ?? "No se pudo cargar la unidad");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Editar unidad</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Editar unidad</h1>
      <p>
        <Link className="back-link" href="/unidades">Volver a la lista</Link>
      </p>
      {loadError && <p role="alert">{loadError}</p>}
      {!unit && !loadError && <p>Cargando...</p>}
      {unit && (
        <UnitForm
          unit={unit}
          onSubmit={(input) => updateUnit(id, input)}
          onSaved={() => router.push("/unidades")}
          onCancel={() => router.push("/unidades")}
        />
      )}
    </main>
  );
}
