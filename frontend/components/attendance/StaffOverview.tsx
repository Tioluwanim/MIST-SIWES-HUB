"use client";
import Link from "next/link";
import { useFetch } from "@/lib/hooks";
import { fmtDate, fmtTime } from "@/lib/format";
import type { Session } from "@/lib/types";
import { BarRow, TrendChart } from "../charts";
import { Badge, Card, Empty, RateText, State, Stat, TableWrap } from "../ui";

interface Agg {
  overall: { total: number; Present: number; Late: number; Absent: number; Excused: number; rate: number };
  by_department: { name: string; total: number; rate: number }[]; by_unit: { name: string; total: number; rate: number }[];
  trend: { date: string; rate: number; total: number }[]; low_attendance: { student_id: number; name: string; rate: number; total: number }[];
}

export function StaffOverview() {
  const agg = useFetch<Agg>("/api/attendance/summary");
  const from = new Date(Date.now() - 30 * 864e5).toISOString().slice(0, 10);
  const sessions = useFetch<Session[]>(`/api/sessions?date_from=${from}`);
  return (
    <div className="space-y-6">
      <State loading={agg.loading} error={agg.error} onRetry={agg.reload}>
        {agg.data && (agg.data.overall.total === 0 ? <Empty title="No attendance recorded yet" hint="Open a session below and start attendance." /> : (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat label="Attendance rate" value={`${agg.data.overall.rate}%`} /><Stat label="Present" value={agg.data.overall.Present} />
              <Stat label="Late" value={agg.data.overall.Late} /><Stat label="Absent" value={agg.data.overall.Absent} />
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <Card title="Attendance by day"><TrendChart data={agg.data.trend} /></Card>
              <Card title="By department and unit"><div className="space-y-3">
                {agg.data.by_department.map((d) => <BarRow key={d.name} label={d.name} value={d.rate} />)}
                <hr className="border-line" />
                {agg.data.by_unit.map((d) => <BarRow key={d.name} label={d.name} value={d.rate} />)}
              </div></Card>
            </div>
            <Card title="Students below 75%">
              {agg.data.low_attendance.length === 0 ? <p className="text-sm text-ink-soft">Everyone is at or above 75%.</p> : (
                <ul className="divide-y divide-line">{agg.data.low_attendance.map((s) => (
                  <li key={s.student_id} className="flex justify-between py-2 text-sm"><span>{s.name}</span><RateText rate={s.rate} total={s.total} /></li>
                ))}</ul>
              )}
            </Card>
          </>
        ))}
      </State>
      <Card title="Sessions (last 30 days and upcoming)">
        <State loading={sessions.loading} error={sessions.error} onRetry={sessions.reload}>
          {sessions.data?.length === 0 ? <Empty title="No sessions" hint="Create a training session to take attendance." /> : (
            <TableWrap>
              <thead><tr><th className="th">Date</th><th className="th">Session</th><th className="th">Class</th><th className="th">Attendance</th><th className="th" /></tr></thead>
              <tbody>{sessions.data?.map((s) => (
                <tr key={s.id}><td className="td">{fmtDate(s.date)}<br /><span className="text-xs text-ink-faint">{fmtTime(s.start_time)}</span></td><td className="td font-medium">{s.title}</td><td className="td">{s.class_name}</td>
                  <td className="td"><Badge>{s.attendance_status}</Badge></td><td className="td"><Link className="btn-secondary btn-sm" href={`/sessions/${s.id}`}>Open</Link></td></tr>
              ))}</tbody>
            </TableWrap>
          )}
        </State>
      </Card>
    </div>
  );
}
