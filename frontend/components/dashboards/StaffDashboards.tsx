"use client";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useFetch } from "@/lib/hooks";
import { fmtDate, fmtTime, firstName, greeting } from "@/lib/format";
import type { Project, Session } from "@/lib/types";
import { Badge, Card, Empty, PageHeader, ProgressBar, State, Stat } from "../ui";

export function InstructorDashboard() {
  const { profile } = useAuth();
  const { data, loading, error, reload } = useFetch<{ today: Session[]; upcoming: Session[]; class_count: number; attendance: { overall: { rate: number; total: number } } }>("/api/dashboard/instructor");
  const row = (s: Session) => (
    <li key={s.id} className="flex items-center justify-between gap-3 py-3 text-sm">
      <span><b>{s.title}</b><br /><span className="text-xs text-ink-faint">{fmtDate(s.date)} · {fmtTime(s.start_time)} · {s.class_name}</span></span>
      <span className="flex items-center gap-2"><Badge>{s.attendance_status}</Badge><Link href={`/sessions/${s.id}`} className="btn-primary btn-sm">{s.attendance_status === "Open" ? "Monitor" : "Open"}</Link></span>
    </li>
  );
  return (
    <>
      <PageHeader title={`${greeting()}, ${firstName(profile!.full_name)}`} subtitle="Your training sessions" />
      <State loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><Stat label="Your classes" value={data.class_count} /><Stat label="Today's sessions" value={data.today.length} /><Stat label="Attendance rate" value={data.attendance.overall.total ? `${data.attendance.overall.rate}%` : "—"} /></div>
            <Card title="Today">{data.today.length ? <ul className="divide-y divide-line">{data.today.map(row)}</ul> : <Empty title="No sessions today" action={<Link className="btn-secondary btn-sm" href="/sessions">Schedule a session</Link>} />}</Card>
            <Card title="Upcoming">{data.upcoming.length ? <ul className="divide-y divide-line">{data.upcoming.map(row)}</ul> : <p className="text-sm text-ink-soft">Nothing scheduled.</p>}</Card>
          </div>
        )}
      </State>
    </>
  );
}

export function SupervisorDashboard() {
  const { profile } = useAuth();
  const { data, loading, error, reload } = useFetch<{ projects: Project[]; pending_reviews: number; student_count: number }>("/api/dashboard/supervisor");
  return (
    <>
      <PageHeader title={`${greeting()}, ${firstName(profile!.full_name)}`} subtitle="Projects you supervise" />
      <State loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="space-y-6">
            <div className="grid grid-cols-3 gap-3"><Stat label="Projects" value={data.projects.length} /><Stat label="Students" value={data.student_count} /><Stat label="Awaiting review" value={data.pending_reviews} /></div>
            {data.pending_reviews > 0 && <Link href="/submissions" className="block rounded-md bg-warn-soft p-3 text-sm font-semibold text-warn">{data.pending_reviews} submission{data.pending_reviews > 1 ? "s" : ""} need your review</Link>}
            <Card title="Your projects">{data.projects.length ? <ul className="space-y-4">{data.projects.map((p) => (
              <li key={p.id}><Link href={`/projects/${p.id}`}><div className="mb-1 flex justify-between text-sm"><b>{p.title}</b><Badge>{p.status}</Badge></div><ProgressBar value={p.progress} /><p className="mt-1 text-xs text-ink-faint">{p.progress}% · {p.members.map((m) => m.name).join(", ")}</p></Link></li>
            ))}</ul> : <Empty title="No projects assigned" hint="The ministry will assign projects to you." />}</Card>
          </div>
        )}
      </State>
    </>
  );
}
