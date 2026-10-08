"use client";
import { Empty, State, TableWrap } from "../ui";
import { fmtDateTime } from "@/lib/format";
import { useFetch } from "@/lib/hooks";

interface Row { id: number; action: string; target_type: string; target_id: string | null; details: Record<string, unknown>; created_at: string }

export function AuditPanel() {
  const { data, loading, error, reload } = useFetch<Row[]>("/api/admin/audit?limit=100");
  return (
    <State loading={loading} error={error} onRetry={reload}>
      {data?.length === 0 ? <Empty title="Nothing logged yet" hint="Seeds, imports, deletions and resets appear here." /> : (
        <TableWrap>
          <thead><tr><th className="th">When</th><th className="th">Action</th><th className="th">Target</th><th className="th">Details</th></tr></thead>
          <tbody>{data?.map((r) => (
            <tr key={r.id}><td className="td whitespace-nowrap">{fmtDateTime(r.created_at)}</td><td className="td font-medium">{r.action.replace(/_/g, " ")}</td>
              <td className="td">{r.target_type}{r.target_id && ` #${r.target_id}`}</td>
              <td className="td max-w-xs truncate text-xs text-ink-soft" title={JSON.stringify(r.details)}>{Object.entries(r.details ?? {}).filter(([, v]) => typeof v !== "object").map(([k, v]) => `${k}: ${v}`).join(" · ") || "—"}</td></tr>))}</tbody>
        </TableWrap>
      )}
    </State>
  );
}
