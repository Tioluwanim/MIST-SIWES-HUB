"use client";
import { useFetch } from "@/lib/hooks";
import { fmtClock, fmtDate, fmtTime } from "@/lib/format";
import type { Session, Stats } from "@/lib/types";
import { Badge, Card, Empty, State, Stat, TableWrap } from "../ui";
import { ScanFlow } from "./ScanFlow";

interface Mine { summary: Stats; history: { id: number; date: string; training: string; session: string; status: string; checked_in_at: string }[] }

export function StudentAttendance() {
  const mine = useFetch<Mine>("/api/attendance/me");
  const today = useFetch<Session[]>("/api/sessions?today=true");
  return (
    <div className="space-y-6">
      {today.data && today.data.length > 0 && (
        <p className="rounded-md bg-brand-soft p-3 text-sm">Today: <b>{today.data[0].title}</b>, {fmtTime(today.data[0].start_time)}–{fmtTime(today.data[0].end_time)}{today.data[0].my_status ? <> · You are marked <b>{today.data[0].my_status}</b></> : null}</p>
      )}
      <ScanFlow onMarked={() => { mine.reload(true); today.reload(true); }} />
      <State loading={mine.loading} error={mine.error} onRetry={mine.reload}>
        {mine.data && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Attendance rate" value={mine.data.summary.total ? `${mine.data.summary.rate}%` : "—"} />
              <Stat label="Total sessions" value={mine.data.summary.total} />
              <Stat label="Present" value={mine.data.summary.present} hint={`${mine.data.summary.late} late`} />
              <Stat label="Absent" value={mine.data.summary.absent} />
            </div>
            <Card title="Attendance history">
              {mine.data.history.length === 0 ? <Empty title="No attendance yet" hint="Your check-ins will appear here after your first session." /> : (
                <TableWrap>
                  <thead><tr><th className="th">Date</th><th className="th">Training</th><th className="th">Session</th><th className="th">Status</th><th className="th">Checked in</th></tr></thead>
                  <tbody>{mine.data.history.map((h) => (
                    <tr key={h.id}><td className="td">{fmtDate(h.date)}</td><td className="td">{h.training}</td><td className="td">{h.session}</td><td className="td"><Badge>{h.status}</Badge></td><td className="td">{h.status === "Absent" ? "—" : fmtClock(h.checked_in_at)}</td></tr>
                  ))}</tbody>
                </TableWrap>
              )}
            </Card>
          </>
        )}
      </State>
    </div>
  );
}
