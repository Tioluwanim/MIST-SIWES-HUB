"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import type { Submission } from "@/lib/types";
import { FileLink } from "../FileLink";
import { FormDialog } from "../FormDialog";
import { Badge } from "../ui";

const Section = ({ label, text }: { label: string; text: string | null }) => text ? <div className="mt-2"><p className="text-xs font-semibold text-ink-soft">{label}</p><p className="whitespace-pre-wrap text-sm">{text}</p></div> : null;

export function SubmissionCard({ s, canReview, showProject, onChanged }: { s: Submission; canReview: boolean; showProject?: boolean; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div><p className="font-bold">{s.title}</p><p className="text-xs text-ink-faint">{s.student_name}{showProject && ` · ${s.project_title}`} · {fmtDateTime(s.created_at)}</p></div>
        <Badge>{s.review_status}</Badge>
      </div>
      <Section label="What I worked on" text={s.worked_on} /><Section label="Challenges" text={s.challenges} /><Section label="Next" text={s.next_steps} />
      {(s.repo_url || s.project_url || s.attachments.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {s.repo_url && <a className="font-semibold text-brand underline" href={s.repo_url} target="_blank" rel="noopener noreferrer">Repository</a>}
          {s.project_url && <a className="font-semibold text-brand underline" href={s.project_url} target="_blank" rel="noopener noreferrer">Live project</a>}
          {s.attachments.map((a) => <FileLink key={a.url} name={a.name} url={a.url} />)}
        </div>
      )}
      {s.feedback && <p className="mt-3 rounded-md bg-surface p-3 text-sm"><span className="text-xs font-semibold text-ink-soft">Supervisor feedback</span><br />{s.feedback}</p>}
      {canReview && <button className="btn-primary btn-sm mt-3" onClick={() => setOpen(true)}>{s.review_status === "Pending" ? "Review" : "Update review"}</button>}
      {open && <FormDialog title={`Review: ${s.title}`} submitLabel="Save review" onClose={() => setOpen(false)} fields={[
        { name: "review_status", label: "Decision", type: "select", required: true, defaultValue: s.review_status === "Pending" ? "" : s.review_status, options: [{ value: "Approved", label: "Approved" }, { value: "Changes Requested", label: "Changes requested" }] },
        { name: "feedback", label: "Feedback", type: "textarea", defaultValue: s.feedback ?? "" },
        ...(s.milestone_id ? [{ name: "mark_milestone_complete", label: "Mark the linked milestone as completed", type: "checkbox" as const }] : [])]}
        onSubmit={async (v) => { await api(`/api/submissions/${s.id}/review`, { method: "PATCH", body: { ...v, mark_milestone_complete: !!v.mark_milestone_complete } }); onChanged(); }} />}
    </article>
  );
}
