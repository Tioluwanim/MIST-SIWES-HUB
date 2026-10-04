"use client";
import { useState } from "react";
import { FormDialog } from "@/components/FormDialog";
import { Badge, Card, Empty, PageHeader, State } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Announcement } from "@/lib/types";

export default function AnnouncementsPage() {
  const { profile } = useAuth();
  const role = profile!.role;
  const canPost = role === "admin" || role === "instructor";
  const { data, loading, error, reload } = useFetch<Announcement[]>("/api/announcements");
  const [open, setOpen] = useState(false);
  const batches = useFetch<{ id: number; name: string }[]>(open && role === "admin" ? "/api/batches" : null);
  const deps = useFetch<{ id: number; name: string }[]>(open && role === "admin" ? "/api/departments" : null);
  const classes = useFetch<{ id: number; name: string }[]>(open ? "/api/training/classes" : null);
  const audiences = role === "admin" ? [{ value: "all", label: "All students" }, { value: "batch", label: "A SIWES batch" }, { value: "department", label: "A department" }, { value: "class", label: "A training class" }] : [{ value: "class", label: "One of my classes" }];
  return (
    <>
      <PageHeader title="Announcements" actions={canPost && <button className="btn-primary" onClick={() => setOpen(true)}>New announcement</button>} />
      <State loading={loading} error={error} onRetry={reload}>
        {data?.length === 0 ? <Empty title="No announcements" /> : <div className="space-y-3">{data?.map((a) => (
          <Card key={a.id}><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-bold">{a.title}</h2><div className="flex items-center gap-2"><Badge>{a.audience === "all" ? "Everyone" : a.audience}</Badge><span className="text-xs text-ink-faint">{fmtDate(a.created_at)}</span></div></div>
            <p className="mt-2 whitespace-pre-wrap text-sm">{a.message}</p>
            {canPost && <button className="mt-3 text-xs font-semibold text-bad" onClick={async () => { if (confirm("Delete this announcement?")) { await api(`/api/announcements/${a.id}`, { method: "DELETE" }).catch((e) => alert(e.message)); reload(true); } }}>Delete</button>}</Card>
        ))}</div>}
      </State>
      {open && <FormDialog title="New announcement" submitLabel="Publish" onClose={() => setOpen(false)} fields={[
        { name: "title", label: "Title", required: true }, { name: "message", label: "Message", type: "textarea", required: true },
        { name: "audience", label: "Send to", type: "select", required: true, options: audiences, defaultValue: audiences[0].value },
        ...(role === "admin" ? [
          { name: "batch_id", label: "Batch (if sending to a batch)", type: "select" as const, options: batches.data?.map((b) => ({ value: b.id, label: b.name })) },
          { name: "department_id", label: "Department (if sending to a department)", type: "select" as const, options: deps.data?.map((b) => ({ value: b.id, label: b.name })) }] : []),
        { name: "class_id", label: "Class (if sending to a class)", type: "select", options: classes.data?.map((c) => ({ value: c.id, label: c.name })) }]}
        onSubmit={async (v) => { await api("/api/announcements", { method: "POST", body: v }); reload(true); }} />}
    </>
  );
}
