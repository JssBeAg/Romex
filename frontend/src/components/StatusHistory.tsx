import type { StatusChange } from "@/lib/reports";

// "2026-10-19 21:30", in the time zone of the person reading
function formatTime(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// The statuses a report has had and when each one began. The status is worked out by the
// system from what happens to the report, so nobody picks it by hand.
export default function StatusHistory({ history }: { history: StatusChange[] }) {
  return (
    <section aria-labelledby="status-history-title">
      <h2 id="status-history-title">Historial de estatus</h2>
      <p className="hint">
        El estatus cambia solo: Pendiente → Asignado (el gerente asigna un mecánico) → Diagnosticado
        → En reparación → Reparado. Si el diagnóstico dice que no requiere reparación, queda en «Sin
        reparación necesaria».
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Estatus</th>
              <th>Desde</th>
              <th>Lo provocó</th>
            </tr>
          </thead>
          <tbody>
            {history.map((change, index) => (
              <tr key={change.id}>
                <td>
                  {change.status}
                  {index === history.length - 1 && <span className="status-current">actual</span>}
                </td>
                <td>{formatTime(change.changed_at)}</td>
                <td>{change.changed_by}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
