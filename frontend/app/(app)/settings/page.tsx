"use client";

import { useMemo, useState } from "react";
import { FormDialog } from "@/components/FormDialog";
import { Badge, Card, Modal, PageHeader, State, TableWrap } from "@/components/ui";
import { api, download, uploadFile } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Profile } from "@/lib/types";

type Tab = "people" | "import" | "tools" | "audit";
type ImportResult = { sheets?: { sheet: string; created: number; updated: number; skipped: number; errors: { row: number; column: string; message: string }[] }[]; errors?: number; total_errors?: number };

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("people");
  const batches = useFetch<{ id: number; name: string; year: number; start_date: string | null; is_active: boolean }[]>("/api/batches");
  const deps = useFetch<{ id: number; name: string }[]>("/api/departments");
  const units = useFetch<{ id: number; name: string; department_id: number }[]>("/api/units");
  const staff = useFetch<Profile[]>("/api/users");
  const audit = useFetch<{ id: number; action: string; target_type: string; details: Record<string, unknown>; created_at: string }[]>("/api/admin/audit?limit=50");
  const [dlg, setDlg] = useState<null | "batch" | "dep" | "unit" | "person">(null);
  const [role, setRole] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Profile | null>(null);
  const [confirm, setConfirm] = useState<Profile | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [csvType, setCsvType] = useState("students");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const people = useMemo(() => (staff.data ?? []).filter((u) =>
    (!role || u.role === role) && (!query || `${u.full_name} ${u.email}`.toLowerCase().includes(query.toLowerCase()))
  ), [staff.data, role, query]);
  const refresh = () => { staff.reload(true); audit.reload(true); };
  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true); setError(null); setMessage(null);
    try { await action(); setMessage(success); refresh(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  async function previewImport() {
    if (!file) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const suffix = file.name.toLowerCase().endsWith(".csv") ? `&type=${encodeURIComponent(csvType)}` : "";
      setImportResult(await uploadFile<ImportResult>(`/api/admin/import?dry_run=true${suffix}`, file));
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  const importRows = importResult?.sheets ?? [];
  const blocking = (importResult?.total_errors ?? importResult?.errors ?? 0) > 0;
  return (
    <>
      <PageHeader title="Settings" subtitle="Manage people, data tools and audit history" />
      <div className="mb-5 flex flex-wrap gap-2 border-b border-line">
        {(["people", "import", "tools", "audit"] as Tab[]).map((name) => <button key={name} className={`border-b-2 px-3 py-2 text-sm font-semibold ${tab === name ? "border-brand text-brand" : "border-transparent text-ink-soft"}`} onClick={() => setTab(name)}>{name[0].toUpperCase() + name.slice(1)}</button>)}
      </div>
      {(message || error) && <div className={`mb-4 rounded-md p-3 text-sm ${error ? "bg-bad-soft text-bad" : "bg-ok-soft text-ok"}`}>{error ?? message}</div>}

      {tab === "people" && <div className="space-y-6">
        <Card title="People" action={<button className="btn-primary btn-sm" onClick={() => setDlg("person")}>Add person</button>}>
          <div className="mb-4 flex flex-wrap gap-3"><input className="input max-w-xs" placeholder="Search name or email" value={query} onChange={(e) => setQuery(e.target.value)} /><select className="input max-w-xs" value={role} onChange={(e) => setRole(e.target.value)}><option value="">All roles</option>{["admin", "instructor", "supervisor", "student"].map((r) => <option key={r}>{r}</option>)}</select></div>
          <State loading={staff.loading} error={staff.error} onRetry={staff.reload}><TableWrap><thead><tr><th className="th">Name</th><th className="th">Role</th><th className="th">Status</th><th className="th" /></tr></thead><tbody>{people.map((u) => <tr key={u.id}><td className="td"><b>{u.full_name}</b><br /><span className="text-xs text-ink-faint">{u.email}</span></td><td className="td"><Badge>{u.role}</Badge></td><td className="td">{u.is_active ? "Active" : "Inactive"}</td><td className="td"><div className="flex justify-end gap-2"><button className="btn-secondary btn-sm" onClick={() => setSelected(u)}>Edit</button><button className="btn-secondary btn-sm" onClick={() => run(() => api(`/api/users/${u.id}`, { method: "PATCH", body: { is_active: !u.is_active } }).then(() => undefined), u.is_active ? "User deactivated." : "User reactivated.")}>{u.is_active ? "Deactivate" : "Reactivate"}</button><button className="btn-secondary btn-sm text-bad" onClick={() => setConfirm(u)}>Delete</button></div></td></tr>)}</tbody></TableWrap></State>
        </Card>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="SIWES batches" action={<button className="btn-secondary btn-sm" onClick={() => setDlg("batch")}>Add batch</button>}><State loading={batches.loading} error={batches.error} onRetry={batches.reload}><ul className="divide-y divide-line text-sm">{batches.data?.map((b) => <li key={b.id} className="flex justify-between py-2"><span><b>{b.name}</b>{b.start_date && <span className="text-ink-faint"> · from {fmtDate(b.start_date)}</span>}</span><Badge>{b.is_active ? "Open" : "Closed"}</Badge></li>)}</ul></State></Card>
          <Card title="Departments and units" action={<span className="flex gap-2"><button className="btn-secondary btn-sm" onClick={() => setDlg("dep")}>Department</button><button className="btn-secondary btn-sm" onClick={() => setDlg("unit")}>Unit</button></span>}><State loading={deps.loading} error={deps.error} onRetry={deps.reload}><ul className="space-y-3 text-sm">{deps.data?.map((d) => <li key={d.id}><b>{d.name}</b><div className="mt-1 flex flex-wrap gap-1">{units.data?.filter((u) => u.department_id === d.id).map((u) => <span key={u.id} className="rounded bg-surface-deep px-2 py-0.5 text-xs">{u.name}</span>)}</div></li>)}</ul></State></Card>
        </div>
      </div>}

      {tab === "import" && <div className="space-y-6"><Card title="Import data"><div className="flex flex-wrap items-center gap-3"><button className="btn-secondary" onClick={() => download("/api/admin/import/template", "siwes-import-template.xlsx")}>Download template</button><label className="btn-secondary cursor-pointer">Choose .xlsx or .csv<input className="hidden" type="file" accept=".xlsx,.csv" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setImportResult(null); }} /></label>{file?.name.endsWith(".csv") && <select className="input max-w-xs" value={csvType} onChange={(e) => setCsvType(e.target.value)}>{["students", "instructors", "supervisors", "admins", "batches", "departments", "units", "programs", "classes", "sessions", "projects"].map((v) => <option key={v}>{v}</option>)}</select>}<button className="btn-primary" disabled={!file || busy} onClick={previewImport}>{busy ? "Checking…" : "Dry run"}</button></div>{file && <p className="mt-3 text-sm text-ink-soft">{file.name}</p>}</Card>
        {importResult && <Card title="Import preview"><TableWrap><thead><tr><th className="th">Sheet</th><th className="th">Create</th><th className="th">Update</th><th className="th">Skip</th><th className="th">Errors</th></tr></thead><tbody>{importRows.map((s) => <tr key={s.sheet}><td className="td">{s.sheet}</td><td className="td">{s.created}</td><td className="td">{s.updated}</td><td className="td">{s.skipped}</td><td className="td">{s.errors.length}</td></tr>)}</tbody></TableWrap>{blocking && <div className="mt-4 max-h-56 overflow-y-auto rounded bg-bad-soft p-3 text-sm text-bad">{importRows.flatMap((s) => s.errors.map((e) => <p key={`${s.sheet}-${e.row}-${e.column}`}>{s.sheet}, row {e.row}, {e.column}: {e.message}</p>))}</div>}<div className="mt-4 flex gap-2"><button className="btn-primary" disabled={busy || blocking} onClick={() => file && run(() => uploadFile(`/api/admin/import?dry_run=false&skip_invalid=false${file.name.endsWith(".csv") ? `&type=${csvType}` : ""}`, file).then((r) => setImportResult(r)), "Import complete.")}>Import everything</button><button className="btn-secondary" disabled={busy || !blocking} onClick={() => file && run(() => uploadFile(`/api/admin/import?dry_run=false&skip_invalid=true${file.name.endsWith(".csv") ? `&type=${csvType}` : ""}`, file).then((r) => setImportResult(r)), "Valid rows imported.")}>Import valid rows only</button></div></Card>)}</div>}

      {tab === "tools" && <div className="grid gap-6 lg:grid-cols-2"><SeedCard run={run} /><Card title="Danger zone" className="border-bad/30"><p className="mb-3 text-sm text-ink-soft">Resets are destructive and require server-side permission.</p><button className="btn-secondary text-bad" onClick={() => setConfirm(null)}>Open reset controls</button><ResetControls run={run} /></Card></div>}
      {tab === "audit" && <Card title="Recent actions"><State loading={audit.loading} error={audit.error} onRetry={audit.reload}><TableWrap><thead><tr><th className="th">Action</th><th className="th">Target</th><th className="th">Date</th></tr></thead><tbody>{audit.data?.map((a) => <tr key={a.id}><td className="td">{a.action}</td><td className="td">{a.target_type}</td><td className="td">{new Date(a.created_at).toLocaleString()}</td></tr>)}</tbody></TableWrap></State></Card>}

      {dlg === "batch" && <FormDialog title="New SIWES batch" onClose={() => setDlg(null)} fields={[{ name: "name", label: "Name", required: true }, { name: "year", label: "Year", type: "number", required: true }, { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" }, { name: "is_active", label: "Active", type: "checkbox", defaultValue: true }]} onSubmit={async (v) => { await api("/api/batches", { method: "POST", body: v }); batches.reload(true); }} />}
      {dlg === "dep" && <FormDialog title="New department" onClose={() => setDlg(null)} fields={[{ name: "name", label: "Name", required: true }, { name: "description", label: "Description", type: "textarea" }]} onSubmit={async (v) => { await api("/api/departments", { method: "POST", body: v }); deps.reload(true); }} />}
      {dlg === "unit" && <FormDialog title="New unit" onClose={() => setDlg(null)} fields={[{ name: "department_id", label: "Department", type: "select", required: true, options: deps.data?.map((d) => ({ value: d.id, label: d.name })) }, { name: "name", label: "Unit name", required: true }]} onSubmit={async (v) => { await api("/api/units", { method: "POST", body: v }); units.reload(true); }} />}
      {(dlg === "person" || selected) && <FormDialog title={selected ? `Edit ${selected.full_name}` : "Add person"} onClose={() => { setDlg(null); setSelected(null); }} fields={[{ name: "full_name", label: "Full name", required: true, defaultValue: selected?.full_name }, { name: "email", label: "Email", type: "email", required: true, defaultValue: selected?.email }, { name: "role", label: "Role", type: "select", required: true, defaultValue: selected?.role, options: ["admin", "instructor", "supervisor", "student"].map((r) => ({ value: r, label: r })) }]} onSubmit={async (v) => { await api(selected ? `/api/users/${selected.id}` : "/api/users", { method: selected ? "PATCH" : "POST", body: v }); refresh(); }} />}
      {confirm && <Modal title="Delete user" onClose={() => setConfirm(null)}><p className="text-sm">Delete <b>{confirm.full_name}</b>? This cannot be undone.</p><div className="mt-4 flex justify-end gap-2"><button className="btn-secondary" onClick={() => setConfirm(null)}>Cancel</button><button className="btn-primary bg-bad" onClick={() => run(() => api(`/api/users/${confirm.id}?hard=true`, { method: "DELETE" }).then(() => setConfirm(null)), "User deleted.")}>Delete</button></div></Modal>}
    </>
  );
}

function SeedCard({ run }: { run: (action: () => Promise<void>, success: string) => Promise<void> }) {
  const [include, setInclude] = useState(true); const [instructor, setInstructor] = useState(""); const [supervisor, setSupervisor] = useState("");
  return <Card title="Demo data"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={include} onChange={(e) => setInclude(e.target.checked)} /> Include demo data</label><input className="input mt-3" placeholder="Instructor email (optional)" value={instructor} onChange={(e) => setInstructor(e.target.value)} /><input className="input mt-3" placeholder="Supervisor email (optional)" value={supervisor} onChange={(e) => setSupervisor(e.target.value)} /><div className="mt-4 flex gap-2"><button className="btn-primary" onClick={() => run(() => api("/api/admin/seed", { method: "POST", body: { include_demo: include, instructor_email: instructor || undefined, supervisor_email: supervisor || undefined } }).then(() => undefined), "Seed complete.")}>Seed demo data</button><button className="btn-secondary text-bad" onClick={() => run(() => api("/api/admin/demo-data", { method: "DELETE" }).then(() => undefined), "Demo data removed.")}>Remove demo data</button></div></Card>;
}

function ResetControls({ run }: { run: (action: () => Promise<void>, success: string) => Promise<void> }) {
  const [scope, setScope] = useState("attendance"); const [confirm, setConfirm] = useState("");
  return <div className="mt-4 space-y-3"><select className="input" value={scope} onChange={(e) => setScope(e.target.value)}>{["attendance", "projects", "announcements", "training", "students", "all_except_admins"].map((s) => <option key={s}>{s}</option>)}</select><input className="input" placeholder='Type RESET to confirm' value={confirm} onChange={(e) => setConfirm(e.target.value)} /><button className="btn-primary bg-bad" disabled={confirm !== "RESET"} onClick={() => run(() => api("/api/admin/reset", { method: "POST", body: { scope, confirm } }).then(() => undefined), "Reset complete.")}>Reset data</button></div>;
}
