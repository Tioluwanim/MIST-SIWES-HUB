"use client";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useFetch } from "@/lib/hooks";
import { DeleteButton } from "../admin/DeleteButton";
import { fmtDate, fmtTime } from "@/lib/format";
import type { Session } from "@/lib/types";
import { Badge, Empty, State, TableWrap } from "../ui";
import { SessionForm } from "./SessionForm";

export function SessionsPanel() {
  const { data, loading, error, reload } = useFetch<Session[]>("/api/sessions");
  const { profile } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <div className="space-y-4">
      <div className="flex justify-end"><button className="btn-primary" onClick={() => setOpen(true)}>New session</button></div>
      <State loading={loading} error={error} onRetry={reload}>
        {data?.length === 0 ? <Empty title="No sessions yet" hint="Create a class first, then schedule sessions for it." action={<button className="btn-primary btn-sm" onClick={() => setOpen(true)}>New session</button>} /> : (
          <TableWrap>
            <thead><tr><th className="th">Date</th><th className="th">Session</th><th className="th">Class</th><th className="th">Venue</th><th className="th">Attendance</th><th className="th" /></tr></thead>
            <tbody>{data?.map((s) => (
              <tr key={s.id}><td className="td whitespace-nowrap">{fmtDate(s.date)}<br /><span className="text-xs text-ink-faint">{fmtTime(s.start_time)}–{fmtTime(s.end_time)}</span></td>
                <td className="td font-medium">{s.title}</td><td className="td">{s.class_name}</td><td className="td text-ink-soft">{s.location ?? "—"}<br /><span className="text-xs">{s.allowed_radius_meters} m radius</span></td>
                <td className="td"><Badge>{s.attendance_status}</Badge></td>
                <td className="td whitespace-nowrap"><Link href={`/sessions/${s.id}`} className="btn-secondary btn-sm">{s.attendance_status === "Open" ? "Monitor" : "Attendance"}</Link>{profile?.role === "admin" && <> <DeleteButton path={`/api/admin/sessions/${s.id}`} noun="session" onDone={() => reload(true)} /></>}</td></tr>
            ))}</tbody>
          </TableWrap>
        )}
      </State>
      {open && <SessionForm onClose={() => setOpen(false)} onSaved={() => reload(true)} />}
    </div>
  );
}
