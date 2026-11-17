"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExportButton from "@/components/ExportButton";
import { COLORS, GroupedBars, HBars } from "@/components/MiniCharts";
import { type Dashboard, getDashboard } from "@/lib/dashboard";
import { MANAGER_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];
const PERIODS = [3, 6, 12];

const money = (value: string | number) =>
  Number(value).toLocaleString("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });

function Kpi({ value, label, alert = false, href }: { value: string | number; label: string; alert?: boolean; href?: string }) {
  const body = (
    <>
      <span className="kpi-value">{value}</span>
      <span className="kpi-label">{label}</span>
    </>
  );
  return href ? (
    <Link href={href} className={`kpi${alert ? " alert" : ""}`} style={{ textDecoration: "none", color: "inherit" }}>
      {body}
    </Link>
  ) : (
    <div className={`kpi${alert ? " alert" : ""}`}>{body}</div>
  );
}

export default function DashboardPage() {
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [months, setMonths] = useState(6);
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    getDashboard(months).then((res) => {
      if (cancelled) return;
      if (res.ok && res.data) {
        setData(res.data);
        setError("");
      } else {
        setError(res.error ?? "No se pudo cargar el dashboard");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [allowed, months]);

  if (loading) return <p>Cargando...</p>;
  if (!allowed) {
    return (
      <main>
        <h1>Dashboard</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  const c = data?.cards;

  return (
    <main>
      <h1>Dashboard e indicadores</h1>
      <p>
        <Link className="back-link" href="/">Volver al inicio</Link>
      </p>

      <div className="list-actions">
        <span className="period-switch" role="group" aria-label="Periodo">
          {PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              className={months === p ? "page-current" : undefined}
              aria-pressed={months === p}
              onClick={() => setMonths(p)}
              style={months === p ? { background: "var(--color-primary)", borderColor: "var(--color-primary)", color: "var(--color-on-primary)" } : undefined}
            >
              {p} meses
            </button>
          ))}
        </span>
        <ExportButton path="dashboard/" params={{ months }} label="Exportar a PDF" />
      </div>
      {data && <p className="hint">Periodo: {data.period.from} al {data.period.to}. Los indicadores se calculan al momento con los registros del sistema.</p>}

      {error && <p role="alert">{error}</p>}
      {!data && !error && <p>Cargando...</p>}

      {data && c && (
        <>
          <h2>Ahora</h2>
          <div className="kpi-grid">
            <Kpi value={c.open_reports} label="Reportes abiertos" href="/reportes" />
            <Kpi value={c.unassigned_reports} label="Abiertos sin mecánico" alert={c.unassigned_reports > 0} href="/reportes" />
            <Kpi value={c.preventive_overdue} label="Preventivo vencido" alert={c.preventive_overdue > 0} href="/preventivo" />
            <Kpi value={c.preventive_upcoming} label="Preventivo próximo" href="/preventivo" />
            <Kpi value={c.low_stock_parts} label="Refacciones con stock bajo" alert={c.low_stock_parts > 0} href="/refacciones" />
            <Kpi value={`${c.active_units} / ${c.inactive_units}`} label="Unidades activas / inactivas" href="/unidades" />
          </div>

          <h2>En los últimos {data.months} meses</h2>
          <div className="kpi-grid">
            <Kpi value={c.reports_in_period} label="Reportes de falla" />
            <Kpi value={c.avg_resolution_days === null ? "—" : `${c.avg_resolution_days} días`} label="Promedio para cerrar un reporte" />
            <Kpi value={c.maintenances_in_period} label="Mantenimientos" />
            <Kpi value={money(c.cost_in_period)} label="Costo de mantenimiento" />
            <Kpi value={money(c.avg_cost)} label="Costo promedio por mantenimiento" />
          </div>

          <div className="chart-grid">
            <section className="chart-card">
              <h2>Reportes de falla por mes</h2>
              <GroupedBars labels={data.monthly.labels} series={[{ name: "Reportes", color: COLORS.main, values: data.monthly.reports }]} />
            </section>
            <section className="chart-card">
              <h2>Mantenimientos por mes</h2>
              <GroupedBars
                labels={data.monthly.labels}
                series={[
                  { name: "Preventivos", color: COLORS.second, values: data.monthly.preventive },
                  { name: "Correctivos", color: COLORS.main, values: data.monthly.corrective },
                ]}
              />
            </section>
            <section className="chart-card">
              <h2>Costo de mantenimiento por mes</h2>
              <GroupedBars
                labels={data.monthly.labels}
                series={[{ name: "Costo (MXN)", color: COLORS.second, values: data.monthly.cost }]}
                format={(n) => (n >= 1000 ? `${Math.round(n / 1000)}k` : String(Math.round(n)))}
              />
            </section>
            <section className="chart-card">
              <h2>Reportes por estatus (hoy)</h2>
              <HBars closedColor rows={data.report_statuses.map((s) => ({ label: s.label, value: s.count, closed: s.closed }))} />
            </section>
            <section className="chart-card">
              <h2>Unidades con más costo de mantenimiento</h2>
              <HBars rows={data.top_units_by_cost.map((u) => ({ label: u.unit, value: Number(u.total) }))} format={money} />
            </section>
            <section className="chart-card">
              <h2>Unidades con más reportes</h2>
              <HBars rows={data.top_units_by_reports.map((u) => ({ label: u.unit, value: u.count }))} />
            </section>
            <section className="chart-card">
              <h2>Refacciones más usadas (piezas)</h2>
              <HBars rows={data.top_parts.map((p) => ({ label: p.part, value: p.pieces }))} />
            </section>
            <section className="chart-card">
              <h2>Carga de mecánicos (reportes abiertos)</h2>
              <HBars rows={data.mechanic_workload.map((m) => ({ label: m.mechanic, value: m.open_reports }))} />
            </section>
          </div>

          {data.low_stock.length > 0 && (
            <>
              <h2>Refacciones por agotarse</h2>
              <ul>
                {data.low_stock.map((p) => (
                  <li key={p.id}>
                    <Link href={`/refacciones/${p.id}`}>{p.name}</Link>: quedan {p.stock} (mínimo {p.min_stock})
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </main>
  );
}
