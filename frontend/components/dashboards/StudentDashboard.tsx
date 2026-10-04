"use client";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useFetch } from "@/lib/hooks";
import { fmtClock, fmtDate, fmtTime, firstName, greeting } from "@/lib/format";
import type { Announcement, Project, Profile, Session, Stats } from "@/lib/types";
import { Badge, Card, Empty, ProgressBar, State } from "../ui";

interface D {
  user: Profile; today: Session[]; upcoming: Session[]; attendance: Stats;
  recent_attendance: { date: string; session: string; status: string; checked_in_at: string }[];
  active_project: Project | null; next_milestone: { title: string; due_date: string | null } | null; announcements: Announcement[];
}

export function StudentDashboard() {
  const { profile } = useAuth();
  const { data, loading, error, reload } = useFetch<D>("/api/dashboard/student");
  return (
    <State loading={loading} error={error} onRetry={reload}>
      {data && (
        <div className="space-y-5">
          <div>
            <h1 className="text-[22px] font-bold sm:text-2xl">{greeting()}, {firstName(profile!.full_name)}</h1>
            <p className="mt-1 text-sm text-ink-soft">{[profile!.unit?.name ?? profile!.department?.name, profile!.batch?.name].filter(Boolean).join(" · ") || "Waiting for the ministry to assign your batch and unit"}</p>
          </div>

          <section className="rounded-lg bg-brand p-5 text-white">
            <p className="text-sm text-white/70">Today&apos;s training</p>
            {data.today.length ? data.today.map((s) => (
              <div key={s.id} className="mt-2">
                <p className="text-lg font-bold">{s.title}</p>
                <p className="text-sm text-white/80">{fmtTime(s.start_time)} – {fmtTime(s.end_time)} · {s.class_name}</p>
                {s.my_status ? <p className="mt-3 text-sm">Attendance: <b>{s.my_status}</b> at {fmtClock(s.my_marked_at)}</p>
                  : <Link href="/attendance" className="mt-4 flex min-h-[48px] items-center justify-center rounded-md bg-white font-bold text-brand">Scan QR for attendance</Link>}
              </div>
            )) : <p className="mt-2 text-white/90">No training scheduled today.{data.upcoming[0] && ` Next: ${data.upcoming[0].title}, ${fmtDate(data.upcoming[0].date)}.`}</p>}
          </section>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Attendance" action={<Link href="/attendance" className="text-sm font-semibold text-brand">View all</Link>}>
              {data.attendance.total ? (
                <>
                  <p className="text-4xl font-bold">{data.attendance.rate}%</p>
                  <p className="mt-1 text-sm text-ink-soft">{data.attendance.total} sessions · {data.attendance.present} present · {data.attendance.late} late · {data.attendance.absent} absent</p>
                  <ul className="mt-4 divide-y divide-line">{data.recent_attendance.map((r, i) => (
                    <li key={i} className="flex items-center justify-between py-2 text-sm"><span>{r.session}<br /><span className="text-xs text-ink-faint">{fmtDate(r.date)}</span></span><Badge>{r.status}</Badge></li>
                  ))}</ul>
                </>
              ) : <Empty title="No attendance yet" hint="Your rate appears after your first session." />}
            </Card>

            <Card title="Active project" action={<Link href="/projects" className="text-sm font-semibold text-brand">Projects</Link>}>
              {data.active_project ? (
                <Link href={`/projects/${data.active_project.id}`} className="block">
                  <p className="font-semibold">{data.active_project.title}</p>
                  <div className="my-3"><ProgressBar value={data.active_project.progress} /></div>
                  <p className="text-sm text-ink-soft">{data.active_project.progress}% complete{data.active_project.deadline && ` · due ${fmtDate(data.active_project.deadline)}`}</p>
                  {data.next_milestone && <p className="mt-3 rounded-md bg-surface p-3 text-sm"><span className="text-ink-soft">Upcoming milestone</span><br /><b>{data.next_milestone.title}</b>{data.next_milestone.due_date && ` · ${fmtDate(data.next_milestone.due_date)}`}</p>}
                </Link>
              ) : <Empty title="No active project" hint="You will see your project here once the ministry assigns you." />}
            </Card>
          </div>

          <Card title="Announcements" action={<Link href="/announcements" className="text-sm font-semibold text-brand">All</Link>}>
            {data.announcements.length ? <ul className="divide-y divide-line">{data.announcements.map((a) => (
              <li key={a.id} className="py-3"><p className="font-semibold">{a.title}</p><p className="mt-0.5 line-clamp-2 text-sm text-ink-soft">{a.message}</p></li>
            ))}</ul> : <p className="text-sm text-ink-soft">Nothing new.</p>}
          </Card>
        </div>
      )}
    </State>
  );
}
