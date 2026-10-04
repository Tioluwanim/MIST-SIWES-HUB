"use client";
import { useState } from "react";
import { api, upload } from "@/lib/api";
import type { Milestone } from "@/lib/types";
import { Modal } from "../ui";

export function SubmitUpdate({ projectId, milestones, onClose, onSaved }: { projectId: number; milestones: Milestone[]; onClose: () => void; onSaved: () => void }) {
  const [v, setV] = useState({ title: "", milestone_id: "", worked_on: "", challenges: "", next_steps: "", repo_url: "", project_url: "" });
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string, val: string) => setV((s) => ({ ...s, [k]: val }));
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      const attachments = [];
      for (const f of files) attachments.push(await upload(f));
      await api("/api/submissions", { method: "POST", body: { project_id: projectId, title: v.title, milestone_id: v.milestone_id ? Number(v.milestone_id) : undefined,
        worked_on: v.worked_on || undefined, challenges: v.challenges || undefined, next_steps: v.next_steps || undefined, repo_url: v.repo_url || undefined, project_url: v.project_url || undefined, attachments } });
      onSaved(); onClose();
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  return (
    <Modal title="Submit a progress update" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <div><label className="label" htmlFor="st">Title *</label><input id="st" required minLength={2} className="input" placeholder="Week 3 Progress" value={v.title} onChange={(e) => set("title", e.target.value)} /></div>
        <div><label className="label" htmlFor="sm">Related milestone</label><select id="sm" className="input" value={v.milestone_id} onChange={(e) => set("milestone_id", e.target.value)}><option value="">None</option>{milestones.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select></div>
        <div><label className="label" htmlFor="sw">What I worked on</label><textarea id="sw" className="input min-h-[80px] py-2" value={v.worked_on} onChange={(e) => set("worked_on", e.target.value)} /></div>
        <div><label className="label" htmlFor="sc">Challenges</label><textarea id="sc" className="input min-h-[64px] py-2" value={v.challenges} onChange={(e) => set("challenges", e.target.value)} /></div>
        <div><label className="label" htmlFor="sn">Next</label><textarea id="sn" className="input min-h-[64px] py-2" value={v.next_steps} onChange={(e) => set("next_steps", e.target.value)} /></div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div><label className="label" htmlFor="sr">Repository URL</label><input id="sr" type="url" className="input" placeholder="https://github.com/…" value={v.repo_url} onChange={(e) => set("repo_url", e.target.value)} /></div>
          <div><label className="label" htmlFor="sp">Project URL</label><input id="sp" type="url" className="input" placeholder="https://" value={v.project_url} onChange={(e) => set("project_url", e.target.value)} /></div>
        </div>
        <div><label className="label" htmlFor="sf">Files (documentation, screenshots)</label><input id="sf" type="file" multiple className="input py-2" onChange={(e) => setFiles(Array.from(e.target.files ?? []).slice(0, 10))} /><p className="mt-1 text-xs text-ink-faint">Up to 10 MB each.</p></div>
        {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={busy}>{busy ? "Submitting…" : "Submit update"}</button></div>
      </form>
    </Modal>
  );
}
