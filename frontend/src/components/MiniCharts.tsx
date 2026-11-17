"use client";

// Small charts drawn with SVG/CSS (no library): few points, easy to read and to copy by hand.
// Colors come from the theme tokens so they follow light and dark mode.

type Series = { name: string; color: string; values: number[] };

const COLORS = {
  main: "var(--color-primary)",
  second: "var(--color-chart-b)",
  third: "var(--color-text-muted)",
};
export { COLORS };

// Bars grouped by label (one bar per series), with the value written on top of each
export function GroupedBars({ labels, series, format = (n: number) => String(n) }: {
  labels: string[];
  series: Series[];
  format?: (value: number) => string;
}) {
  const width = 360;
  const height = 190;
  const left = 8;
  const bottom = 24;
  const top = 18;
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const groupWidth = (width - left * 2) / labels.length;
  const barWidth = Math.min(26, (groupWidth - 8) / series.length);
  const plotHeight = height - bottom - top;

  return (
    <>
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img"
        aria-label={`Gráfica de barras: ${series.map((s) => s.name).join(", ")} por mes`}>
        <line className="axis" x1={left} x2={width - left} y1={height - bottom} y2={height - bottom} />
        {labels.map((label, i) => {
          const x0 = left + i * groupWidth + (groupWidth - barWidth * series.length) / 2;
          return (
            <g key={label}>
              {series.map((s, j) => {
                const value = s.values[i] ?? 0;
                const h = (value / max) * plotHeight;
                return (
                  <g key={s.name}>
                    <rect x={x0 + j * barWidth} y={height - bottom - h} width={barWidth - 2} height={h} rx={2} fill={s.color}>
                      <title>{`${s.name}, ${label}: ${format(value)}`}</title>
                    </rect>
                    {value > 0 && (
                      <text x={x0 + j * barWidth + (barWidth - 2) / 2} y={height - bottom - h - 4} textAnchor="middle">
                        {format(value)}
                      </text>
                    )}
                  </g>
                );
              })}
              <text x={left + i * groupWidth + groupWidth / 2} y={height - 8} textAnchor="middle">{label}</text>
            </g>
          );
        })}
      </svg>
      {series.length > 1 && (
        <div className="legend">
          {series.map((s) => (
            <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>
          ))}
        </div>
      )}
    </>
  );
}

// Horizontal bars: one row per item, the longest fills the line
export function HBars({ rows, format = (n: number) => String(n), closedColor = false }: {
  rows: { label: string; value: number; closed?: boolean }[];
  format?: (value: number) => string;
  closedColor?: boolean;
}) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (rows.length === 0) return <p className="hint">Sin datos en este periodo.</p>;
  return (
    <div>
      {rows.map((row) => (
        <div className="bar-row" key={row.label}>
          <span className="bar-label" title={row.label}>{row.label}</span>
          <span className="bar-track" aria-hidden="true">
            <span className={`bar-fill${closedColor && row.closed ? " closed" : ""}`} style={{ width: `${(row.value / max) * 100}%` }} />
          </span>
          <span className="bar-value">{format(row.value)}</span>
        </div>
      ))}
    </div>
  );
}
