"use client";
import Link from "next/link";
import { useFetch } from "@/lib/hooks";
import { fmtClock, fmtDate, fmtTime } from "@/lib/format";
import type { Project, Session } from "@/lib/types";
import { BarRow, TrendChart } from "../charts";
import { Badge, Card, PageHeader, ProgressBar, RateText, State, Stat } from "../ui";

interface D {
  total_interns: number; today_sessions: Session[]; today: { present: number; late: number; absent: number }; overall_rate: number; active_projects: number;
  trend: { date: string; rate: number; total: number }[]; by_department: { name: string; rate: number; total: number }[];
  low_attendance: { student_id: number; name: string; rate: number; total: number }[];
  recent_activity: { student: string; session: string; status: string; method: string; at: string }[]; projects: Project[]; upcoming: Session[];
}

export function AdminDashboard() {
  const { data, loading, error, reload } = useFetch<D>("/api/dashboard/admin");
  return (
    <>
      <PageHeader title="Dashboard" subtitle="SIWES operations at a glance" />
      <State loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
              <Stat label="Total interns" value={data.total_interns} /><Stat label="Today's sessions" value={data.today_sessions.length} />
              <Stat label="Present today" value={data.today.present} /><Stat label="Late today" value={data.today.late} />
              <Stat label="Absent today" value={data.today.absent} /><Stat label="Overall rate" value={`${data.overall_rate}%`} /><Stat label="Active projects" value={data.active_projects} />
            </div>
            <div className="grid gap-6 lg:grid-cols-3">
              <Card title="Attendance trend" className="lg:col-span-2">{data.trend.length ? <TrendChart data={data.trend} /> : <p className="text-sm text-ink-soft">No attendance data yet.</p>}</Card>
              <Card title="By department"><div className="space-y-3">{data.by_department.length ? data.by_department.map((d) => <BarRow key={d.name} label={d.name} value={d.rate} />) : <p className="text-sm text-ink-soft">No data yet.</p>}</div></Card>
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <Card title="Recent attendance activity">
                {data.recent_activity.length ? <ul className="divide-y divide-line">{data.recent_activity.map((a, i) => (
                  <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm"><span><b>{a.student}</b><br /><span className="text-xs text-ink-faint">{a.session} · {fmtClock(a.at)} · {a.method}</span></span><Badge>{a.status}</Badge></li>
                ))}</ul> : <p className="text-sm text-ink-soft">Nothing yet.</p>}
              </Card>
              <Card title="Students below 75% attendance" action={<Link className="text-sm font-semibold text-brand" href="/reports">Report</Link>}>
                {data.low_attendance.length ? <ul className="divide-y divide-line">{data.low_attendance.map((s) => (
                  <li key={s.student_id} className="flex justify-between py-2 text-sm"><span>{s.name}</span><RateText rate={s.rate} total={s.total} /></li>
                ))}</ul> : <p className="text-sm text-ink-soft">No one is below the threshold.</p>}
              </Card>
              <Card title="Active projects" action={<Link className="text-sm font-semibold text-brand" href="/projects">All projects</Link>}>
                {data.projects.length ? <ul className="space-y-4">{data.projects.map((p) => (
                  <li key={p.id}><Link href={`/projects/${p.id}`} className="block"><div className="mb-1 flex justify-between gap-2 text-sm"><b>{p.title}</b><Badge>{p.status}</Badge></div><ProgressBar value={p.progress} /><p className="mt-1 text-xs text-ink-faint">{p.progress}% · {p.member_count} students{p.deadline && ` · due ${fmtDate(p.deadline)}`}</p></Link></li>
                ))}</ul> : <p className="text-sm text-ink-soft">No active projects.</p>}
              </Card>
              <Card title="Upcoming training" action={<Link className="text-sm font-semibold text-brand" href="/training">Manage</Link>}>
                {data.upcoming.length ? <ul className="divide-y divide-line">{data.upcoming.map((s) => (
                  <li key={s.id} className="py-2 text-sm"><b>{s.title}</b><br /><span className="text-xs text-ink-faint">{fmtDate(s.date)} · {fmtTime(s.start_time)} · {s.class_name}</span></li>
                ))}</ul> : <p className="text-sm text-ink-soft">Nothing scheduled.</p>}
              </Card>
            </div>
          </div>
        )}
      </State>
    </>
  );
}
