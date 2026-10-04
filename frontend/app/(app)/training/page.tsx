"use client";
import { useState } from "react";
import { FormDialog } from "@/components/FormDialog";
import { Materials } from "@/components/training/Materials";
import { SessionsPanel } from "@/components/training/SessionsPanel";
import { Badge, Card, Empty, PageHeader, State, TableWrap } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { fmtDate, fmtTime } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Session } from "@/lib/types";

interface Cls { id: number; name: string; program_name: string; batch_name: string; instructor_name: string | null; student_count: number | null }

function ClassList({ canEdit }: { canEdit: boolean }) {
  const { data, loading, error, reload } = useFetch<Cls[]>("/api/training/classes");
  const [openId, setOpenId] = useState<number | null>(null);
  return (
    <State loading={loading} error={error} onRetry={reload}>
      {data?.length === 0 ? <Empty title="No classes yet" hint={canEdit ? "Create a class to get started." : "You will see your classes once you are enrolled."} /> : (
        <div className="grid gap-4 md:grid-cols-2">{data?.map((c) => (
          <Card key={c.id}>
            <p className="font-bold">{c.name}</p>
            <p className="text-sm text-ink-soft">{c.program_name} · {c.batch_name}</p>
            <p className="mt-1 text-sm text-ink-soft">{c.instructor_name ? `Instructor: ${c.instructor_name}` : "No instructor assigned"}{canEdit && c.student_count != null && ` · ${c.student_count} students`}</p>
            <button className="btn-secondary btn-sm mt-3" onClick={() => setOpenId(openId === c.id ? null : c.id)}>{openId === c.id ? "Hide materials" : "Materials"}</button>
            {openId === c.id && <div className="mt-3 border-t border-line pt-3"><Materials classId={c.id} canEdit={canEdit} /></div>}
          </Card>
        ))}</div>
      )}
    </State>
  );
}

function StudentTraining() {
  const { data, loading, error, reload } = useFetch<Session[]>("/api/sessions?upcoming=true");
  return (
    <div className="space-y-6">
      <Card title="Upcoming sessions">
        <State loading={loading} error={error} onRetry={reload}>
          {data?.length ? <TableWrap><thead><tr><th className="th">Date</th><th className="th">Session</th><th className="th">Class</th><th className="th">Venue</th></tr></thead>
            <tbody>{data.map((s) => <tr key={s.id}><td className="td whitespace-nowrap">{fmtDate(s.date)}<br /><span className="text-xs text-ink-faint">{fmtTime(s.start_time)}–{fmtTime(s.end_time)}</span></td><td className="td font-medium">{s.title}</td><td className="td">{s.class_name}</td><td className="td">{s.location ?? "—"}</td></tr>)}</tbody></TableWrap>
            : <Empty title="Nothing scheduled" hint="New sessions will show up here." />}
        </State>
      </Card>
      <div><h2 className="mb-3 text-[15px] font-bold">Your classes</h2><ClassList canEdit={false} /></div>
    </div>
  );
}

function AdminTraining() {
  const [tab, setTab] = useState<"classes" | "sessions">("classes");
  const [dlg, setDlg] = useState<null | "program" | "class">(null);
  const [rev, setRev] = useState(0);
  const batches = useFetch<{ id: number; name: string }[]>("/api/batches");
  const programs = useFetch<{ id: number; name: string; batch_name: string }[]>(`/api/training/programs?r=${rev}`);
  const instructors = useFetch<{ id: number; full_name: string }[]>("/api/users?role=instructor");
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 border-b border-line">
        {(["classes", "sessions"] as const).map((t) => <button key={t} onClick={() => setTab(t)} className={`min-h-[44px] border-b-2 px-4 text-sm font-semibold ${tab === t ? "border-brand text-brand" : "border-transparent text-ink-soft"}`}>{t === "classes" ? "Programs & classes" : "Sessions"}</button>)}
      </div>
      {tab === "sessions" ? <SessionsPanel /> : (
        <>
          <div className="flex flex-wrap gap-2"><button className="btn-primary" onClick={() => setDlg("program")}>New program</button><button className="btn-secondary" onClick={() => setDlg("class")}>New class</button></div>
          <Card title="Programs"><State loading={programs.loading} error={programs.error} onRetry={programs.reload}>
            {programs.data?.length ? <ul className="divide-y divide-line text-sm">{programs.data.map((p) => <li key={p.id} className="flex justify-between py-2"><b>{p.name}</b><Badge>{p.batch_name}</Badge></li>)}</ul> : <p className="text-sm text-ink-soft">No programs yet. Create a SIWES batch in Settings first, then add a program.</p>}
          </State></Card>
          <ClassList key={rev} canEdit />
        </>
      )}
      {dlg === "program" && <FormDialog title="New training program" onClose={() => setDlg(null)} fields={[
        { name: "batch_id", label: "SIWES batch", type: "select", required: true, options: batches.data?.map((b) => ({ value: b.id, label: b.name })) },
        { name: "name", label: "Program name", required: true, placeholder: "Software Development Training" }, { name: "description", label: "Description", type: "textarea" }]}
        onSubmit={async (v) => { await api("/api/training/programs", { method: "POST", body: v }); setRev((r) => r + 1); }} />}
      {dlg === "class" && <FormDialog title="New training class" onClose={() => setDlg(null)} fields={[
        { name: "program_id", label: "Program", type: "select", required: true, options: programs.data?.map((p) => ({ value: p.id, label: `${p.name} (${p.batch_name})` })) },
        { name: "name", label: "Class name", required: true, placeholder: "Backend Development" },
        { name: "instructor_id", label: "Instructor", type: "select", options: instructors.data?.map((i) => ({ value: i.id, label: i.full_name })) },
        { name: "enroll_batch", label: "Enrol every student in the batch", type: "checkbox", defaultValue: true }]}
        onSubmit={async (v) => { await api("/api/training/classes", { method: "POST", body: v }); setRev((r) => r + 1); }} />}
    </div>
  );
}

export default function TrainingPage() {
  const { profile } = useAuth();
  const role = profile!.role;
  return (
    <>
      <PageHeader title="Training" subtitle={role === "admin" ? "Programs, classes and sessions" : role === "instructor" ? "Your classes and materials" : "Your schedule and classes"} />
      {role === "admin" ? <AdminTraining /> : role === "instructor" ? <ClassList canEdit /> : <StudentTraining />}
    </>
  );
}
