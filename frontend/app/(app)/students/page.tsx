"use client";
import { useState } from "react";
import { FormDialog } from "@/components/FormDialog";
import { Empty, PageHeader, RateText, State, TableWrap } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Profile, Stats } from "@/lib/types";

type Row = Profile & { attendance: Stats };

export default function StudentsPage() {
  const { profile } = useAuth();
  const admin = profile!.role === "admin";
  const [q, setQ] = useState("");
  const [batch, setBatch] = useState("");
  const [rev, setRev] = useState(0);
  const params = new URLSearchParams({ ...(q ? { q } : {}), ...(batch ? { batch_id: batch } : {}), r: String(rev) });
  const { data, loading, error, reload } = useFetch<Row[]>(`/api/students?${params}`);
  const batches = useFetch<{ id: number; name: string }[]>("/api/batches");
  const deps = useFetch<{ id: number; name: string }[]>(admin ? "/api/departments" : null);
  const units = useFetch<{ id: number; name: string; department_id: number }[]>(admin ? "/api/units" : null);
  const [dlg, setDlg] = useState<null | "new" | Row>(null);
  const bOpts = batches.data?.map((b) => ({ value: b.id, label: b.name }));
  const dOpts = deps.data?.map((d) => ({ value: d.id, label: d.name }));
  const uOpts = units.data?.map((u) => ({ value: u.id, label: u.name }));
  const done = () => setRev((r) => r + 1);

  return (
    <>
      <PageHeader title={admin ? "Interns" : "Students"} subtitle="SIWES students and their attendance" actions={admin && <button className="btn-primary" onClick={() => setDlg("new")}>Register intern</button>} />
      <div className="mb-4 flex flex-wrap gap-3">
        <input className="input max-w-xs" placeholder="Search name, email or matric no." aria-label="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input max-w-xs" aria-label="Batch" value={batch} onChange={(e) => setBatch(e.target.value)}><option value="">All batches</option>{bOpts?.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}</select>
      </div>
      <State loading={loading} error={error} onRetry={reload}>
        {data?.length === 0 ? <Empty title="No students found" hint={admin ? "Register interns or change your filters. Students who sign up on their own appear here too." : undefined} /> : (
          <TableWrap>
            <thead><tr><th className="th">Name</th><th className="th">Batch</th><th className="th">Department / unit</th><th className="th">Sessions</th><th className="th">Rate</th>{admin && <th className="th" />}</tr></thead>
            <tbody>{data?.map((s) => (
              <tr key={s.id}><td className="td"><b>{s.full_name}</b><br /><span className="text-xs text-ink-faint">{s.email}{s.matric_no && ` · ${s.matric_no}`}{s.phone && ` · ${s.phone}`}</span></td>
                <td className="td">{s.batch?.name ?? <span className="text-warn">Unassigned</span>}</td>
                <td className="td">{s.department?.name ?? "—"}{s.unit && <><br /><span className="text-xs text-ink-faint">{s.unit.name}</span></>}</td>
                <td className="td">{s.attendance.total}</td><td className="td"><RateText rate={s.attendance.rate} total={s.attendance.total} /></td>
                {admin && <td className="td"><button className="btn-secondary btn-sm" onClick={() => setDlg(s)}>Assign</button></td>}</tr>
            ))}</tbody>
          </TableWrap>
        )}
      </State>
      {dlg === "new" && <FormDialog title="Register intern" submitLabel="Register" onClose={() => setDlg(null)} fields={[
        { name: "full_name", label: "Full name", required: true }, { name: "email", label: "Email", type: "email", required: true, help: "The intern signs in with this email to activate the account." },
        { name: "matric_no", label: "Matric number" }, { name: "institution", label: "Institution" },
        { name: "batch_id", label: "SIWES batch", type: "select", options: bOpts }, { name: "department_id", label: "Department", type: "select", options: dOpts }, { name: "unit_id", label: "Unit", type: "select", options: uOpts }]}
        onSubmit={async (v) => { await api("/api/users", { method: "POST", body: { ...v, role: "student" } }); done(); }} />}
      {dlg && dlg !== "new" && <FormDialog title={`Assign ${dlg.full_name}`} onClose={() => setDlg(null)} fields={[
        { name: "batch_id", label: "SIWES batch", type: "select", options: bOpts, defaultValue: dlg.batch?.id ?? "" },
        { name: "department_id", label: "Department", type: "select", options: dOpts, defaultValue: dlg.department?.id ?? "" },
        { name: "unit_id", label: "Unit", type: "select", options: uOpts, defaultValue: dlg.unit?.id ?? "" }]}
        onSubmit={async (v) => { await api(`/api/users/${dlg.id}`, { method: "PATCH", body: v }); done(); }} />}
    </>
  );
}
