"use client";

import { type KeyboardEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import ExportButton from "@/components/ExportButton";
import KardexSection, { LongText } from "@/components/KardexSection";
import {
  type KardexChange,
  type KardexChecklist,
  type KardexEvent,
  type KardexFault,
  type KardexHeader,
  type KardexMaintenance,
  type KardexPart,
  type KardexPerson,
  getKardex,
} from "@/lib/kardex";
import { MANAGER_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

const ALLOWED_ROLES = [MANAGER_ROLE];

const money = (value: string) => Number(value).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
const yesNo = (value: boolean) => (value ? "Sí" : "No");

// The sections, in the order of the tabs; the id is also the #hash of the address
const TABS = [
  { id: "mantenimientos", label: "Mantenimientos" },
  { id: "fallas", label: "Fallas" },
  { id: "checklists", label: "Checklists" },
  { id: "refacciones", label: "Refacciones cambiadas" },
  { id: "operadores", label: "Operadores y mecánicos" },
  { id: "cambios", label: "Placas y cambios de datos" },
  { id: "linea-de-tiempo", label: "Línea de tiempo" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function List({ items }: { items: string[] }) {
  if (items.length === 0) return <>—</>;
  if (items.length === 1) return <>{items[0]}</>;
  return (
    <ul className="cell-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default function KardexPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { loading, allowed } = useRoleGuard(ALLOWED_ROLES);
  const [kardex, setKardex] = useState<KardexHeader | null>(null);
  const [loadError, setLoadError] = useState("");
  const [tab, setTab] = useState<TabId>("mantenimientos");

  useEffect(() => {
    if (!allowed) return;
    getKardex(id).then((res) => {
      if (res.ok && res.data) setKardex(res.data);
      else setLoadError(res.error ?? "No se pudo cargar el kardex");
    });
  }, [allowed, id]);

  // The tab in the address (#fallas...) survives a reload and can be linked
  useEffect(() => {
    const fromHash = window.location.hash.slice(1);
    if (TABS.some((t) => t.id === fromHash)) setTab(fromHash as TabId);
  }, []);

  function choose(next: TabId) {
    setTab(next);
    window.history.replaceState(null, "", `#${next}`);
  }

  // Arrow keys move between the tabs (the usual keyboard pattern of a tab list)
  function onTabKey(e: KeyboardEvent<HTMLDivElement>) {
    const index = TABS.findIndex((t) => t.id === tab);
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = TABS[(index + step + TABS.length) % TABS.length].id;
    choose(next);
    document.getElementById(`tab-${next}`)?.focus();
  }

  if (loading) return <p>Cargando...</p>;

  if (!allowed) {
    return (
      <main>
        <h1>Kardex</h1>
        <p role="alert">No tienes acceso a esta sección.</p>
        <p>
          <Link className="back-link" href="/">Volver al inicio</Link>
        </p>
      </main>
    );
  }

  const unit = kardex?.unit;
  const s = kardex?.summary;

  return (
    <main>
      <h1>{unit ? `Kardex de la unidad ${unit.economic_number}` : "Kardex"}</h1>
      <p>
        <Link className="back-link" href="/kardex">Volver a la lista</Link>
      </p>
      <div className="list-actions">
        <ExportButton path={`kardex/${id}/`} label="Exportar kardex completo" />
      </div>
      {loadError && <p role="alert">{loadError}</p>}
      {!kardex && !loadError && <p>Cargando...</p>}

      {kardex && unit && s && (
        <>
          <h2>Datos de la unidad</h2>
          <div className="table-scroll"><table>
            <tbody>
              <tr><th>Número económico</th><td>{unit.economic_number}</td></tr>
              <tr><th>Marca y modelo</th><td>{unit.brand.label} / {unit.unit_model.label}</td></tr>
              <tr>
                <th>Placa actual</th>
                <td>
                  {unit.current_plate
                    ? `${unit.current_plate.identifier} (${unit.current_plate.state})`
                    : "Sin placa vigente"}
                </td>
              </tr>
              <tr><th>Kilometraje actual</th><td>{unit.mileage} km</td></tr>
              <tr>
                <th>Operador</th>
                <td>
                  {unit.current_operator
                    ? `${unit.current_operator.operator.label}, desde ${unit.current_operator.start_date}`
                    : "Sin operador"}
                </td>
              </tr>
            </tbody>
          </table></div>

          <h2>Resumen</h2>
          <div className="table-scroll"><table>
            <tbody>
              <tr>
                <th>Reportes de fallas</th>
                <td>{s.reports} ({s.pending_reports} abiertos)</td>
              </tr>
              <tr><th>Diagnósticos</th><td>{s.diagnoses}</td></tr>
              <tr>
                <th>Mantenimientos</th>
                <td>
                  {s.maintenances} ({s.preventive_maintenances} preventivos, {s.corrective_maintenances} correctivos)
                </td>
              </tr>
              <tr><th>Costo total de mantenimientos</th><td>{money(s.total_maintenance_cost)}</td></tr>
              <tr>
                <th>Último mantenimiento</th>
                <td>
                  {s.last_maintenance
                    ? `${s.last_maintenance.date} a los ${s.last_maintenance.mileage} km`
                    : "Sin mantenimientos"}
                </td>
              </tr>
              <tr>
                <th>Checklists</th>
                <td>
                  {s.checklists}
                  {s.last_checklist && ` (el último: ${s.last_checklist.date}, ${s.last_checklist.mileage} km)`}
                </td>
              </tr>
            </tbody>
          </table></div>

          <h2>Mantenimiento preventivo</h2>
          {kardex.preventive.length === 0 ? (
            <p>No hay planes preventivos activos para esta unidad.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Plan</th>
                    <th>Estado</th>
                    <th>Detalle</th>
                    <th>Último servicio</th>
                  </tr>
                </thead>
                <tbody>
                  {kardex.preventive.map((row) => (
                    <tr key={row.plan.id}>
                      <td>{row.plan.name}</td>
                      <td><span className={`status-badge ${row.status === "vencido" ? "overdue" : row.status === "proximo" ? "upcoming" : row.status === "al_corriente" ? "ok" : "no_history"}`}>{row.status_label}</span></td>
                      <td>{row.message}</td>
                      <td>{row.last ? `${row.last.date}, ${row.last.mileage} km` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="tabs" role="tablist" aria-label="Secciones del kardex" onKeyDown={onTabKey}>
            {TABS.map((t) => (
              <button
                key={t.id}
                id={`tab-${t.id}`}
                type="button"
                role="tab"
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                tabIndex={tab === t.id ? 0 : -1}
                onClick={() => choose(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Only the open tab is mounted: each section asks the server for its rows when it is opened */}
          <section className="tab-panel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            {tab === "mantenimientos" && (
              <KardexSection<KardexMaintenance>
                unitId={id}
                section="mantenimientos"
                rowsKey="maintenances"
                title="Mantenimientos"
                searchLabel="Buscar (refacción, responsable, causa u observaciones)"
                filters={[
                  { name: "tipo", label: "Tipo de servicio", all: "Todos", options: [{ id: "preventivo", label: "Preventivo" }, { id: "correctivo", label: "Correctivo" }] },
                  { name: "terminada", label: "Reparación terminada", all: "Todas", options: [{ id: "si", label: "Sí" }, { id: "no", label: "No" }] },
                ]}
                rowKey={(m) => m.id}
                empty="Sin mantenimientos con estos filtros."
                columns={[
                  { header: "Fecha", sort: "date", cell: (m) => m.date },
                  { header: "Mantenimiento", cell: (m) => <Link href={`/mantenimientos/${m.id}`}>{m.folio}</Link> },
                  { header: "Servicio", cell: (m) => <>{m.service_type}{m.plan && <div className="hint">{m.plan}</div>}</> },
                  { header: "Km", sort: "mileage", cell: (m) => m.mileage },
                  { header: "Costo", sort: "cost", cell: (m) => money(m.cost) },
                  { header: "Responsables", cell: (m) => <List items={m.people} /> },
                  { header: "Refacciones", cell: (m) => (m.parts.length ? <List items={m.parts.map((p) => `${p.label} × ${p.quantity}`)} /> : "Sin refacciones") },
                  { header: "Reparación terminada", cell: (m) => (m.repair_completed === null ? "—" : yesNo(m.repair_completed)) },
                  {
                    header: "Reporte / diagnóstico",
                    cell: (m) =>
                      m.report || m.diagnosis ? (
                        <>
                          {m.report && <div><Link href={`/reportes/${m.report.id}`}>{m.report.label}</Link></div>}
                          {m.diagnosis && <div><Link href={`/diagnosticos/${m.diagnosis.id}`}>{m.diagnosis.label}</Link></div>}
                        </>
                      ) : (
                        "—"
                      ),
                  },
                  { header: "Causa", cell: (m) => <LongText text={m.cause} /> },
                  { header: "Observaciones", cell: (m) => <LongText text={m.observations} /> },
                ]}
              />
            )}

            {tab === "fallas" && (
              <KardexSection<KardexFault>
                unitId={id}
                section="fallas"
                rowsKey="faults"
                title="Fallas"
                searchLabel="Buscar (descripción, ubicación o causa)"
                filters={[{ name: "estatus", label: "Estatus", all: "Todos", options: (page) => page?.statuses ?? [] }]}
                rowKey={(r) => r.id}
                empty="Sin reportes de falla con estos filtros."
                columns={[
                  { header: "Fecha", sort: "date", cell: (r) => r.date },
                  { header: "Reporte", cell: (r) => <><Link href={`/reportes/${r.id}`}>{r.folio}</Link><div className="hint">{r.reported_by}</div></> },
                  { header: "Ubicación", cell: (r) => r.location },
                  { header: "Descripción", cell: (r) => <LongText text={r.description} /> },
                  { header: "Estatus", sort: "status", cell: (r) => r.status },
                  { header: "Mecánico", cell: (r) => <List items={r.mechanics} /> },
                  { header: "Diagnóstico", cell: (r) => (r.diagnosis ? <Link href={`/diagnosticos/${r.diagnosis.id}`}>{r.diagnosis.folio}</Link> : "Sin diagnóstico") },
                  { header: "Causa", cell: (r) => <LongText text={r.diagnosis?.cause} /> },
                  { header: "Gravedad", cell: (r) => r.diagnosis?.severity ?? "—" },
                  { header: "¿Puede operar?", cell: (r) => (r.diagnosis ? yesNo(r.diagnosis.unit_operable) : "—") },
                ]}
              />
            )}

            {tab === "checklists" && (
              <KardexSection<KardexChecklist>
                unitId={id}
                section="checklists"
                rowsKey="checklists"
                title="Checklists"
                searchLabel="Buscar (operador o viaje)"
                filters={[{ name: "resultado", label: "Resultado", all: "Todos", options: [{ id: "ok", label: "Todo bien" }, { id: "fallas", label: "Con fallas" }] }]}
                rowKey={(c) => c.id}
                empty="Sin checklists con estos filtros."
                columns={[
                  { header: "Fecha", sort: "date", cell: (c) => c.date },
                  { header: "Checklist", cell: (c) => <Link href={`/checklists/${c.id}`}>{c.folio}</Link> },
                  { header: "Operador", cell: (c) => c.operator },
                  { header: "Km", sort: "mileage", cell: (c) => c.mileage },
                  {
                    header: "Resultado",
                    cell: (c) =>
                      c.ok ? (
                        <span className="status-badge ok">Todo bien</span>
                      ) : (
                        <span className="status-badge overdue">Con fallas: {c.failed_items.join(", ")}</span>
                      ),
                  },
                  { header: "Viaje", cell: (c) => <LongText text={c.trip_description} /> },
                ]}
              />
            )}

            {tab === "refacciones" && (
              <KardexSection<KardexPart>
                unitId={id}
                section="refacciones"
                rowsKey="parts"
                title="Refacciones cambiadas"
                searchLabel="Buscar refacción"
                rowKey={(p) => p.id}
                empty="A esta unidad no se le ha cambiado ninguna refacción con estos filtros."
                columns={[
                  { header: "Refacción", sort: "part", cell: (p) => p.label },
                  { header: "Piezas", sort: "pieces", cell: (p) => p.pieces },
                  { header: "Veces", sort: "times", cell: (p) => p.times },
                  { header: "Último cambio", sort: "last_date", cell: (p) => p.last_date },
                ]}
              />
            )}

            {tab === "operadores" && (
              <KardexSection<KardexPerson>
                unitId={id}
                section="operadores"
                rowsKey="people"
                title="Operadores y mecánicos"
                searchLabel="Buscar persona"
                filters={[{ name: "rol", label: "Rol", all: "Todos", options: [{ id: "operador", label: "Operadores" }, { id: "mecanico", label: "Mecánicos" }] }]}
                rowKey={(p) => p.id}
                empty="Nadie ha tenido ni atendido esta unidad en ese periodo."
                columns={[
                  { header: "Rol", cell: (p) => p.role },
                  { header: "Persona", sort: "person", cell: (p) => p.person },
                  { header: "Desde", sort: "start_date", cell: (p) => p.start_date },
                  { header: "Hasta", sort: "end_date", cell: (p) => p.end_date ?? "Actual" },
                  { header: "Reporte", cell: (p) => (p.report ? <Link href={`/reportes/${p.report.id}`}>{p.report.label}</Link> : "—") },
                ]}
              />
            )}

            {tab === "cambios" && (
              <>
                <h3>Placas</h3>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Placa</th>
                        <th>Estado</th>
                        <th>Desde</th>
                        <th>Hasta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {unit.plate_history.length === 0 && (
                        <tr>
                          <td colSpan={4}>Sin placas.</td>
                        </tr>
                      )}
                      {unit.plate_history.map((p) => (
                        <tr key={`${p.identifier}-${p.start_date}`}>
                          <td>{p.identifier}</td>
                          <td>{p.state}</td>
                          <td>{p.start_date}</td>
                          <td>{p.end_date ?? "Vigente"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h3>Cambios de datos</h3>
                <p className="hint">
                  Cada corrección al número económico, modelo, kilometraje o si está activa. Las placas y los operadores
                  tienen su propia tabla.
                </p>
                <KardexSection<KardexChange>
                  unitId={id}
                  section="cambios"
                  rowsKey="changes"
                  title="Cambios de datos"
                  searchLabel="Buscar (campo o valor)"
                  filters={[{ name: "usuario", label: "Usuario", all: "Todos", options: (page) => page?.users ?? [] }]}
                  rowKey={(c) => c.id}
                  empty="Los datos de la unidad no se han modificado con estos filtros."
                  columns={[
                    { header: "Fecha y hora", sort: "moment", cell: (c) => c.moment },
                    { header: "Campo", sort: "field", cell: (c) => c.field },
                    { header: "Antes", cell: (c) => <LongText text={c.old} /> },
                    { header: "Después", cell: (c) => <LongText text={c.new} /> },
                    { header: "Quién", cell: (c) => c.user },
                  ]}
                />
              </>
            )}

            {tab === "linea-de-tiempo" && (
              <KardexSection<KardexEvent>
                unitId={id}
                section="linea-de-tiempo"
                rowsKey="events"
                title="Línea de tiempo"
                searchLabel="Buscar en la línea de tiempo"
                filters={[{ name: "tipo", label: "Tipo de evento", all: "Todos", options: (page) => page?.types ?? [] }]}
                rowKey={(e) => `${e.type}-${e.date}-${e.title}-${e.detail}`}
                empty="Sin eventos con estos filtros."
                columns={[
                  { header: "Fecha", sort: "date", cell: (e) => e.date },
                  { header: "Tipo", cell: (e) => e.type_label },
                  { header: "Evento", cell: (e) => (e.link ? <Link href={e.link}>{e.title}</Link> : e.title) },
                  { header: "Detalle", cell: (e) => <LongText text={e.detail} limit={120} /> },
                ]}
              />
            )}
          </section>
        </>
      )}
    </main>
  );
}
