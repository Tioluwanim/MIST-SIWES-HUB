"use client";
import { useState } from "react";
import { FormDialog } from "@/components/FormDialog";
import { Card, PageHeader, State, Badge } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Profile } from "@/lib/types";

export default function SettingsPage() {
  const batches = useFetch<{ id: number; name: string; year: number; start_date: string | null; is_active: boolean }[]>("/api/batches");
  const deps = useFetch<{ id: number; name: string }[]>("/api/departments");
  const units = useFetch<{ id: number; name: string; department_id: number }[]>("/api/units");
  const staff = useFetch<Profile[]>("/api/users");
  const [dlg, setDlg] = useState<null | "batch" | "dep" | "unit" | "staff">(null);
  const staffRows = staff.data?.filter((u) => u.role !== "student");
  return (
    <>
      <PageHeader title="Settings" subtitle="Batches, departments, units and staff accounts" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="SIWES batches" action={<button className="btn-secondary btn-sm" onClick={() => setDlg("batch")}>Add batch</button>}>
          <State loading={batches.loading} error={batches.error} onRetry={batches.reload}><ul className="divide-y divide-line text-sm">{batches.data?.map((b) => <li key={b.id} className="flex justify-between py-2"><span><b>{b.name}</b>{b.start_date && <span className="text-ink-faint"> · from {fmtDate(b.start_date)}</span>}</span><Badge>{b.is_active ? "Open" : "Closed"}</Badge></li>)}</ul></State>
        </Card>
        <Card title="Departments and units" action={<span className="flex gap-2"><button className="btn-secondary btn-sm" onClick={() => setDlg("dep")}>Department</button><button className="btn-secondary btn-sm" onClick={() => setDlg("unit")}>Unit</button></span>}>
          <State loading={deps.loading} error={deps.error} onRetry={deps.reload}><ul className="space-y-3 text-sm">{deps.data?.map((d) => <li key={d.id}><b>{d.name}</b><div className="mt-1 flex flex-wrap gap-1">{units.data?.filter((u) => u.department_id === d.id).map((u) => <span key={u.id} className="rounded bg-surface-deep px-2 py-0.5 text-xs">{u.name}</span>)}</div></li>)}</ul></State>
        </Card>
        <Card title="Staff accounts" className="lg:col-span-2" action={<button className="btn-secondary btn-sm" onClick={() => setDlg("staff")}>Add staff</button>}>
          <State loading={staff.loading} error={staff.error} onRetry={staff.reload}>
            <ul className="divide-y divide-line text-sm">{staffRows?.map((u) => <li key={u.id} className="flex items-center justify-between gap-3 py-2"><span><b>{u.full_name}</b><br /><span className="text-xs text-ink-faint">{u.email}</span></span><span className="flex items-center gap-2"><Badge>{u.role}</Badge></span></li>)}</ul>
          </State>
          <p className="mt-3 text-xs text-ink-faint">Staff sign in with the same email you enter here (Google or email/password). The email must be verified to activate the role.</p>
        </Card>
      </div>
      {dlg === "batch" && <FormDialog title="New SIWES batch" onClose={() => setDlg(null)} fields={[{ name: "name", label: "Name", required: true, placeholder: "2027 SIWES Batch" }, { name: "year", label: "Year", type: "number", required: true, defaultValue: new Date().getFullYear() + 1 }, { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" }, { name: "is_active", label: "Active", type: "checkbox", defaultValue: true }]}
        onSubmit={async (v) => { await api("/api/batches", { method: "POST", body: v }); batches.reload(true); }} />}
      {dlg === "dep" && <FormDialog title="New department" onClose={() => setDlg(null)} fields={[{ name: "name", label: "Name", required: true }, { name: "description", label: "Description", type: "textarea" }]}
        onSubmit={async (v) => { await api("/api/departments", { method: "POST", body: v }); deps.reload(true); }} />}
      {dlg === "unit" && <FormDialog title="New unit" onClose={() => setDlg(null)} fields={[{ name: "department_id", label: "Department", type: "select", required: true, options: deps.data?.map((d) => ({ value: d.id, label: d.name })) }, { name: "name", label: "Unit name", required: true }]}
        onSubmit={async (v) => { await api("/api/units", { method: "POST", body: v }); units.reload(true); }} />}
      {dlg === "staff" && <FormDialog title="Add staff account" submitLabel="Add" onClose={() => setDlg(null)} fields={[{ name: "full_name", label: "Full name", required: true }, { name: "email", label: "Email", type: "email", required: true },
        { name: "role", label: "Role", type: "select", required: true, options: ["instructor", "supervisor", "admin"].map((r) => ({ value: r, label: r })) },
        { name: "department_id", label: "Department", type: "select", options: deps.data?.map((d) => ({ value: d.id, label: d.name })) }]}
        onSubmit={async (v) => { await api("/api/users", { method: "POST", body: v }); staff.reload(true); }} />}
    </>
  );
}
