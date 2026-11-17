"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import WorkerForm from "@/components/WorkerForm";
import { useManagerGuard } from "@/lib/useManagerGuard";
import { type Worker, getWorker, updateWorker } from "@/lib/workers";

export default function EditWorkerPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useManagerGuard();
  const [worker, setWorker] = useState<Worker | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    getWorker(id).then((res) => {
      if (res.ok && res.data) setWorker(res.data.worker);
      else setLoadError(res.error ?? "No se pudo cargar al trabajador");
    });
  }, [allowed, id]);

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Editar trabajador</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>Editar trabajador</h1>
      <p>
        <Link className="back-link" href="/trabajadores">Volver a la lista</Link>
      </p>
      {loadError && <p role="alert">{loadError}</p>}
      {!worker && !loadError && <p>Cargando...</p>}
      {worker && (
        <WorkerForm
          worker={worker}
          onSubmit={(input) => updateWorker(id, input)}
          onSaved={() => router.push("/trabajadores")}
          onCancel={() => router.push("/trabajadores")}
        />
      )}
    </main>
  );
}
