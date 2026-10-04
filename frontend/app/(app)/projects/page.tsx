"use client";
import Link from "next/link";
import { useState } from "react";
import { FormDialog } from "@/components/FormDialog";
import { Badge, Empty, PageHeader, ProgressBar, State } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Project } from "@/lib/types";

export default function ProjectsPage() {
  const { profile } = useAuth();
  const admin = profile!.role === "admin";
  const { data, loading, error, reload } = useFetch<Project[]>("/api/projects");
  const [open, setOpen] = useState(false);
  const batches = useFetch<{ id: number; name: string }[]>(admin ? "/api/batches" : null);
  const students = useFetch<{ student_id: number; full_name: string }[]>(admin ? "/api/students" : null);
  const sups = useFetch<{ id: number; full_name: string }[]>(admin ? "/api/users?role=supervisor" : null);
  return (
    <>
      <PageHeader title="Projects" subtitle={admin ? "Create projects and assign teams" : "Your assigned projects"} actions={admin && <button className="btn-primary" onClick={() => setOpen(true)}>New project</button>} />
      <State loading={loading} error={error} onRetry={reload}>
        {data?.length === 0 ? <Empty title="No projects yet" hint={admin ? "Create a project, then assign students and a supervisor." : "Your projects will appear here once assigned."} /> : (
          <div className="grid gap-4 md:grid-cols-2">{data?.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="card block p-4 hover:border-brand sm:p-5">
              <div className="flex items-start justify-between gap-2"><p className="font-bold">{p.title}</p><Badge>{p.status}</Badge></div>
              <p className="mt-1 line-clamp-2 text-sm text-ink-soft">{p.description}</p>
              <div className="my-3"><ProgressBar value={p.progress} /></div>
              <p className="text-xs text-ink-faint">{p.progress}% complete · {p.member_count} student{p.member_count === 1 ? "" : "s"}{p.supervisors[0] && ` · ${p.supervisors.map((s) => s.name).join(", ")}`}{p.deadline && ` · due ${fmtDate(p.deadline)}`}</p>
            </Link>
          ))}</div>
        )}
      </State>
      {open && <FormDialog title="New project" submitLabel="Create project" onClose={() => setOpen(false)} fields={[
        { name: "title", label: "Title", required: true }, { name: "description", label: "Description", type: "textarea" },
        { name: "batch_id", label: "SIWES batch", type: "select", options: batches.data?.map((b) => ({ value: b.id, label: b.name })) },
        { name: "start_date", label: "Start date", type: "date" }, { name: "deadline", label: "Deadline", type: "date" },
        { name: "member_ids", label: "Students", type: "multiselect", options: students.data?.map((s) => ({ value: s.student_id, label: s.full_name })) },
        { name: "supervisor_ids", label: "Supervisors", type: "multiselect", options: sups.data?.map((s) => ({ value: s.id, label: s.full_name })) },
        { name: "milestones", label: "Milestones (one per line)", type: "textarea", defaultValue: "Requirements\nDatabase Design\nBackend\nFrontend\nTesting\nDeployment\nDocumentation" }]}
        onSubmit={async (v) => {
          const milestones = String(v.milestones ?? "").split("\n").map((t) => t.trim()).filter(Boolean).map((title) => ({ title }));
          await api("/api/projects", { method: "POST", body: { ...v, milestones } }); reload(true);
        }} />}
    </>
  );
}
