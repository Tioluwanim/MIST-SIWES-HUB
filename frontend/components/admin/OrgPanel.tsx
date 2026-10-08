"use client";
import { useState } from "react";
import { FormDialog } from "../FormDialog";
import { Badge, Card, State } from "../ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import { DeleteButton } from "./DeleteButton";

export function OrgPanel() {
  const batches = useFetch<{ id: number; name: string; year: number; start_date: string | null; is_active: boolean }[]>("/api/batches");
  const deps = useFetch<{ id: number; name: string }[]>("/api/departments");
  const units = useFetch<{ id: number; name: string; department_id: number }[]>("/api/units");
  const [dlg, setDlg] = useState<null | "batch" | "dep" | "unit">(null);
  const reloadAll = () => { batches.reload(true); deps.reload(true); units.reload(true); };
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="SIWES batches" action={<button className="btn-secondary btn-sm" onClick={() => setDlg("batch")}>Add batch</button>}>
        <State loading={batches.loading} error={batches.error} onRetry={batches.reload}>
          {batches.data?.length ? <ul className="divide-y divide-line text-sm">{batches.data.map((b) => (
            <li key={b.id} className="flex items-center justify-between gap-2 py-2">
              <span><b>{b.name}</b>{b.start_date && <span className="text-ink-faint"> · from {fmtDate(b.start_date)}</span>}</span>
              <span className="flex items-center gap-2"><Badge>{b.is_active ? "Open" : "Closed"}</Badge><DeleteButton path={`/api/admin/batches/${b.id}`} noun="batch" onDone={reloadAll} /></span>
            </li>))}</ul> : <p className="text-sm text-ink-soft">No batches yet. Add one so students can be placed in a cohort.</p>}
        </State>
      </Card>
      <Card title="Departments and units" action={<span className="flex gap-2"><button className="btn-secondary btn-sm" onClick={() => setDlg("dep")}>Department</button><button className="btn-secondary btn-sm" onClick={() => setDlg("unit")}>Unit</button></span>}>
        <p className="mb-3 rounded-md bg-surface p-3 text-xs text-ink-soft">Students choose their own department and unit from these lists, so set them up before students sign in.</p>
        <State loading={deps.loading} error={deps.error} onRetry={deps.reload}>
          {deps.data?.length ? <ul className="space-y-3 text-sm">{deps.data.map((d) => (
            <li key={d.id}>
              <div className="flex items-center justify-between gap-2"><b>{d.name}</b><DeleteButton path={`/api/admin/departments/${d.id}`} noun="department" onDone={reloadAll} /></div>
              <div className="mt-1 flex flex-wrap gap-1.5">{units.data?.filter((u) => u.department_id === d.id).map((u) => (
                <span key={u.id} className="inline-flex items-center gap-1 rounded bg-surface-deep py-0.5 pl-2 text-xs">{u.name}
                  <DeleteButton path={`/api/admin/units/${u.id}`} noun="unit" label="×" onDone={reloadAll} className="px-1.5 text-bad" /></span>))}</div>
            </li>))}</ul> : <p className="text-sm text-ink-soft">No departments yet.</p>}
        </State>
      </Card>
      {dlg === "batch" && <FormDialog title="New SIWES batch" onClose={() => setDlg(null)} fields={[
        { name: "name", label: "Name", required: true, placeholder: "2027 SIWES Batch" },
        { name: "year", label: "Year", type: "number", required: true, defaultValue: new Date().getFullYear() },
        { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" },
        { name: "is_active", label: "Active", type: "checkbox", defaultValue: true }]}
        onSubmit={async (v) => { await api("/api/batches", { method: "POST", body: v }); batches.reload(true); }} />}
      {dlg === "dep" && <FormDialog title="New department" onClose={() => setDlg(null)} fields={[
        { name: "name", label: "Name", required: true }, { name: "description", label: "Description", type: "textarea" }]}
        onSubmit={async (v) => { await api("/api/departments", { method: "POST", body: v }); deps.reload(true); }} />}
      {dlg === "unit" && <FormDialog title="New unit" onClose={() => setDlg(null)} fields={[
        { name: "department_id", label: "Department", type: "select", required: true, options: deps.data?.map((d) => ({ value: d.id, label: d.name })) },
        { name: "name", label: "Unit name", required: true }]}
        onSubmit={async (v) => { await api("/api/units", { method: "POST", body: v }); units.reload(true); }} />}
    </div>
  );
}
