"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { DeleteButton } from "@/components/admin/DeleteButton";
import { FormDialog } from "@/components/FormDialog";
import { SubmissionCard } from "@/components/projects/SubmissionCard";
import { SubmitUpdate } from "@/components/projects/SubmitUpdate";
import { Badge, Card, Empty, PageHeader, ProgressBar, State } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Project, Submission } from "@/lib/types";

const PROJECT_STATUS = ["Not Started", "In Progress", "Under Review", "Completed"];

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const { profile } = useAuth();
  const role = profile!.role;
  const router = useRouter();
  const p = useFetch<Project>(`/api/projects/${id}`);
  const subs = useFetch<Submission[]>(`/api/submissions?project_id=${id}`);
  const [dlg, setDlg] = useState<null | "milestone" | "assign" | "submit">(null);
  const [err, setErr] = useState<string | null>(null);
  const manage = role === "admin" || role === "supervisor";
  const students = useFetch<{ student_id: number; full_name: string }[]>(role === "admin" ? "/api/students" : null);
  const sups = useFetch<{ id: number; full_name: string }[]>(role === "admin" ? "/api/users?role=supervisor" : null);

  const refresh = () => { p.reload(true); subs.reload(true); };
  async function run(fn: () => Promise<unknown>) { setErr(null); try { await fn(); refresh(); } catch (e) { setErr((e as Error).message); } }

  return (
    <State loading={p.loading} error={p.error} onRetry={p.reload}>
      {p.data && (
        <>
          <PageHeader title={p.data.title} subtitle={p.data.description ?? undefined} actions={<>
            <Link href="/projects" className="btn-secondary btn-sm">All projects</Link>
            {role === "admin" && <DeleteButton path={`/api/admin/projects/${id}`} noun="project" onDone={() => router.push("/projects")} />}
            {role === "student" && <button className="btn-primary btn-sm" onClick={() => setDlg("submit")}>Submit update</button>}
          </>} />
          {err && <p className="mb-4 rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{err}</p>}
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="space-y-6 lg:col-span-2">
              <Card title="Progress">
                <div className="mb-2 flex items-center justify-between"><span className="text-3xl font-bold">{p.data.progress}%</span>
                  {manage ? <select aria-label="Project status" className="input !w-auto" value={p.data.status} onChange={(e) => run(() => api(`/api/projects/${id}`, { method: "PATCH", body: { status: e.target.value } }))}>{PROJECT_STATUS.map((s) => <option key={s}>{s}</option>)}</select> : <Badge>{p.data.status}</Badge>}</div>
                <ProgressBar value={p.data.progress} />
                <p className="mt-2 text-sm text-ink-soft">{p.data.start_date && `Started ${fmtDate(p.data.start_date)} · `}Deadline {fmtDate(p.data.deadline)}</p>
              </Card>
              <Card title="Milestones" action={manage && <button className="btn-secondary btn-sm" onClick={() => setDlg("milestone")}>Add milestone</button>}>
                {p.data.milestones?.length ? <ul className="divide-y divide-line">{p.data.milestones.map((m) => (
                  <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                    <div><p className="font-semibold">{m.title}</p><p className="text-xs text-ink-faint">{m.due_date ? `Due ${fmtDate(m.due_date)}` : "No due date"}{m.completed_at && ` · completed ${fmtDate(m.completed_at)}`}</p></div>
                    <div className="flex items-center gap-2">{role === "admin" && <DeleteButton path={`/api/admin/milestones/${m.id}`} noun="milestone" onDone={refresh} />}
                    {manage ? <select aria-label={`Status of ${m.title}`} className="input !w-auto" value={m.status} onChange={(e) => run(() => api(`/api/milestones/${m.id}`, { method: "PATCH", body: { status: e.target.value } }))}>{["Not Started", "In Progress", "Completed"].map((s) => <option key={s}>{s}</option>)}</select> : <Badge>{m.status}</Badge>}</div>
                  </li>))}</ul> : <Empty title="No milestones" />}
              </Card>
              <section>
                <h2 className="mb-3 text-[15px] font-bold">Progress updates</h2>
                <State loading={subs.loading} error={subs.error} onRetry={subs.reload}>
                  {subs.data?.length ? <div className="space-y-3">{subs.data.map((s) => <SubmissionCard key={s.id} s={s} canReview={manage} onChanged={refresh} />)}</div>
                    : <Empty title="No updates yet" hint={role === "student" ? "Submit your first progress update." : undefined} />}
                </State>
              </section>
            </div>
            <div className="space-y-6">
              <Card title="Team" action={role === "admin" && <button className="btn-secondary btn-sm" onClick={() => setDlg("assign")}>Assign</button>}>
                <p className="text-xs font-semibold text-ink-soft">Students</p>
                <ul className="mb-3 mt-1 space-y-1 text-sm">{p.data.members.map((m) => <li key={m.student_id}>{m.name}</li>)}{p.data.members.length === 0 && <li className="text-ink-faint">None assigned</li>}</ul>
                <p className="text-xs font-semibold text-ink-soft">Supervisors</p>
                <ul className="mt-1 space-y-1 text-sm">{p.data.supervisors.map((s) => <li key={s.id}>{s.name}</li>)}{p.data.supervisors.length === 0 && <li className="text-ink-faint">None assigned</li>}</ul>
              </Card>
            </div>
          </div>
          {dlg === "milestone" && <FormDialog title="Add milestone" onClose={() => setDlg(null)} fields={[{ name: "title", label: "Title", required: true }, { name: "description", label: "Description", type: "textarea" }, { name: "due_date", label: "Due date", type: "date" }]}
            onSubmit={async (v) => { await api(`/api/projects/${id}/milestones`, { method: "POST", body: v }); refresh(); }} />}
          {dlg === "assign" && <FormDialog title="Assign people" submitLabel="Assign" onClose={() => setDlg(null)} fields={[
            { name: "student_ids", label: "Students", type: "multiselect", options: students.data?.filter((s) => !p.data!.members.some((m) => m.student_id === s.student_id)).map((s) => ({ value: s.student_id, label: s.full_name })) },
            { name: "supervisor_ids", label: "Supervisors", type: "multiselect", options: sups.data?.filter((s) => !p.data!.supervisors.some((x) => x.id === s.id)).map((s) => ({ value: s.id, label: s.full_name })) }]}
            onSubmit={async (v) => { await api(`/api/projects/${id}/assign`, { method: "POST", body: v }); refresh(); }} />}
          {dlg === "submit" && <SubmitUpdate projectId={Number(id)} milestones={p.data.milestones ?? []} onClose={() => setDlg(null)} onSaved={refresh} />}
        </>
      )}
    </State>
  );
}
