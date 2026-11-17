"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import WorkerForm from "@/components/WorkerForm";
import { useManagerGuard } from "@/lib/useManagerGuard";
import { createWorker } from "@/lib/workers";

export default function NewWorkerPage() {
  const router = useRouter();
  const { loading, allowed } = useManagerGuard();

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Nuevo trabajador</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Nuevo trabajador</h1>
      <p>
        <Link className="back-link" href="/trabajadores">Volver a la lista</Link>
      </p>
      <WorkerForm
        onSubmit={createWorker}
        onSaved={() => router.push("/trabajadores")}
        onCancel={() => router.push("/trabajadores")}
      />
    </main>
  );
}
