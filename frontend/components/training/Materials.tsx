"use client";
import { useState } from "react";
import { api, upload } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { fmtDate } from "@/lib/format";
import { FileLink } from "../FileLink";
import { Modal, State } from "../ui";

export function Materials({ classId, canEdit }: { classId: number; canEdit: boolean }) {
  const { data, loading, error, reload } = useFetch<{ id: number; title: string; url: string; created_at: string | null }[]>(`/api/training/classes/${classId}/materials`);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const link = file ? (await upload(file)).url : url;
      if (!link) throw new Error("Choose a file or enter a link");
      await api(`/api/training/classes/${classId}/materials`, { method: "POST", body: { title, url: link } });
      setOpen(false); setTitle(""); setUrl(""); setFile(null); reload(true);
    } catch (e2) { setErr((e2 as Error).message); } finally { setBusy(false); }
  }
  return (
    <div>
      <State loading={loading} error={error} onRetry={reload}>
        {data?.length ? <ul className="divide-y divide-line text-sm">{data.map((m) => <li key={m.id} className="flex justify-between gap-3 py-2"><FileLink name={m.title} url={m.url} /><span className="text-xs text-ink-faint">{fmtDate(m.created_at)}</span></li>)}</ul> : <p className="text-sm text-ink-soft">No materials yet.</p>}
      </State>
      {canEdit && <button className="btn-secondary btn-sm mt-3" onClick={() => setOpen(true)}>Add material</button>}
      {open && (
        <Modal title="Add training material" onClose={() => setOpen(false)}>
          <form onSubmit={save} className="space-y-4">
            <div><label className="label" htmlFor="mt">Title *</label><input id="mt" required minLength={2} className="input" value={title} onChange={(e) => setTitle(e.target.value)} /></div>
            <div><label className="label" htmlFor="mf">Upload a file</label><input id="mf" type="file" className="input py-2" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /><p className="mt-1 text-xs text-ink-faint">PDF, Office files, images, CSV, TXT or ZIP up to 10 MB.</p></div>
            <div><label className="label" htmlFor="mu">…or a link</label><input id="mu" type="url" className="input" placeholder="https://" value={url} disabled={!!file} onChange={(e) => setUrl(e.target.value)} /></div>
            {err && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{err}</p>}
            <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Add"}</button></div>
          </form>
        </Modal>
      )}
    </div>
  );
}
