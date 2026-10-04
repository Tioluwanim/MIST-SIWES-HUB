"use client";

/** Attendance rate per session day. Plain SVG - no charting library needed. */
export function TrendChart({ data }: { data: { date: string; rate: number; total: number }[] }) {
  if (!data.length) return null;
  const w = 560, h = 160, pad = 24, bw = Math.min(36, (w - pad * 2) / data.length - 8);
  return (
    <svg viewBox={`0 0 ${w} ${h + 22}`} className="w-full" role="img" aria-label="Attendance rate by day">
      {[0, 50, 100].map((t) => (
        <g key={t}>
          <line x1={pad} x2={w - pad} y1={h - (t / 100) * (h - 10)} y2={h - (t / 100) * (h - 10)} stroke="#E4DED8" strokeDasharray={t ? "3 4" : ""} />
          <text x={0} y={h - (t / 100) * (h - 10) + 4} fontSize="10" fill="#8B837D">{t}</text>
        </g>
      ))}
      {data.map((d, i) => {
        const x = pad + (i + 0.5) * ((w - pad * 2) / data.length) - bw / 2;
        const bh = (d.rate / 100) * (h - 10);
        return (
          <g key={d.date}>
            <rect x={x} y={h - bh} width={bw} height={bh} rx={3} fill={d.rate < 75 ? "#9B2C2C" : "#5A3825"}><title>{`${d.date}: ${d.rate}%`}</title></rect>
            <text x={x + bw / 2} y={h + 14} fontSize="10" textAnchor="middle" fill="#5E5650">{d.date.slice(5)}</text>
          </g>
        );
      })}
    </svg>
  );
}

export function BarRow({ label, value, sub }: { label: string; value: number; sub?: string }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm"><span className="font-medium">{label}</span><span className="text-ink-soft">{sub ?? `${value}%`}</span></div>
      <div className="h-2 rounded bg-surface-deep"><div className={`h-full rounded ${value < 75 ? "bg-bad" : "bg-brand"}`} style={{ width: `${value}%` }} /></div>
    </div>
  );
}
