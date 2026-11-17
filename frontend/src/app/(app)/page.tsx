"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { navItemsFor } from "@/components/AppShell";
import { getCurrentUser, type User } from "@/lib/api";
import { MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE } from "@/lib/roles";
import { getDue, type DueSummary } from "@/lib/preventive";
import { listSpareParts } from "@/lib/spareParts";

// One short line per section, depending on what the role can do there
function describe(href: string, role: string): string {
  switch (href) {
    case "/reportes":
      if (role === OPERATOR_ROLE) return "Registra las fallas de tus unidades y consulta su estatus.";
      if (role === MECHANIC_ROLE) return "Consulta los reportes de fallas de las unidades.";
      return "Consulta todos los reportes de fallas.";
    case "/checklists":
      return role === OPERATOR_ROLE
        ? "Registra y administra los checklists de tus unidades."
        : "Consulta los checklists que registran los operadores.";
    case "/diagnosticos":
      return role === MECHANIC_ROLE
        ? "Registra y administra tus diagnósticos."
        : "Consulta los diagnósticos de los mecánicos.";
    case "/mantenimientos":
      return role === MECHANIC_ROLE
        ? "Registra y administra tus mantenimientos."
        : "Consulta los mantenimientos realizados.";
    case "/trabajadores":
      return "Da de alta, edita y desactiva a los trabajadores.";
    case "/unidades":
      return "Administra las unidades por su número económico, kilometraje y placas.";
    case "/preventivo":
      return role === MECHANIC_ROLE
        ? "Consulta qué unidades necesitan mantenimiento preventivo, por kilómetros o por días."
        : "Alertas de mantenimiento preventivo por unidad y administración de los planes.";
    case "/refacciones":
      return "Administra el catálogo de refacciones, sus existencias, entradas y alertas de stock bajo.";
    case "/kardex":
      return "Consulta el historial completo de cada unidad: placas, fallas, diagnósticos, mantenimientos y checklists.";
    default:
      return "";
  }
}

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [lowStock, setLowStock] = useState(0); // spare parts with low stock (managers)
  const [due, setDue] = useState<DueSummary | null>(null); // preventive maintenance alerts

  // Protected page: no session means back to the login screen
  useEffect(() => {
    getCurrentUser().then((currentUser) => {
      if (!currentUser) {
        router.replace("/login");
        return;
      }
      setUser(currentUser);
      setLoading(false);
    });
  }, [router]);

  // The manager is warned when spare parts are running out
  useEffect(() => {
    if (user?.role !== MANAGER_ROLE) return;
    listSpareParts({ low: true, status: "active", page_size: 1 }).then((res) => {
      if (res.ok && res.data) setLowStock(res.data.low_stock_count);
    });
  }, [user]);

  // Managers and mechanics are warned about the preventive maintenance that is due
  useEffect(() => {
    if (user?.role !== MANAGER_ROLE && user?.role !== MECHANIC_ROLE) return;
    getDue().then((res) => {
      if (res.ok && res.data) setDue(res.data.summary);
    });
  }, [user]);

  if (loading || !user) return <p>Cargando...</p>;

  const sections = navItemsFor(user.role).filter((item) => item.href !== "/");

  return (
    <main>
      <h1>
        Hola, {user.first_name} {user.paternal_surname}
      </h1>
      <p className="welcome">
        Matrícula {user.enrollment_id} · {user.role}
        {user.is_staff && user.role !== MANAGER_ROLE ? " · Acceso al panel de administración" : ""}
      </p>

      {due && (due.overdue > 0 || due.upcoming > 0) && (
        <p role="status" className="stock-warning">
          Mantenimiento preventivo: {due.overdue} {due.overdue === 1 ? "vencido" : "vencidos"} y {due.upcoming}{" "}
          {due.upcoming === 1 ? "próximo" : "próximos"}. <Link href="/preventivo">Ver detalle</Link>
        </p>
      )}

      {lowStock > 0 && (
        <p role="status" className="stock-warning">
          {lowStock} {lowStock === 1 ? "refacción tiene" : "refacciones tienen"} stock bajo.{" "}
          <Link href="/refacciones">Ver refacciones</Link>
        </p>
      )}

      {sections.length === 0 ? (
        <p>Tu rol no tiene secciones disponibles en este sistema.</p>
      ) : (
        <div className="card-grid">
          {sections.map((item) => (
            <Link key={item.href} href={item.href} className="link-card">
              <strong>{item.label}</strong>
              <span>{describe(item.href, user.role)}</span>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
