"use client";
import { useState } from "react";
import { FormDialog } from "../FormDialog";
import { Badge, Empty, Modal, State, TableWrap } from "../ui";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Profile } from "@/lib/types";

const ROLES = ["admin", "instructor", "supervisor", "student"];

export function PeoplePanel() {
  const [role, setRole] = useState("");
  const [q, setQ] = useState("");
  const qs = new URLSearchParams({ ...(role ? { role } : {}), ...(q ? { q } : {}) }).toString();
  const users = useFetch<Profile[]>(`/api/users${qs ? `?${qs}` : ""}`);
  const deps = useFetch<{ id: number; name: string }[]>("/api/departments");
  const units = useFetch<{ id: number; name: string; department_id: number }[]>("/api/units");
  const batches = useFetch<{ id: number; name: string }[]>("/api/batches");
  const [dlg, setDlg] = useState<null | "add" | Profile>(null);
  const [hard, setHard] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hardError, setHardError] = useState<string | null>(null);

  const depOpts = deps.data?.map((d) => ({ value: d.id, label: d.name }));
  const unitOpts = units.data?.map((u) => ({ value: u.id, label: `${u.name} (${deps.data?.find((d) => d.id === u.department_id)?.name ?? "?"})` }));
  const batchOpts = batches.data?.map((b) => ({ value: b.id, label: b.name }));
  const act = async (fn: () => Promise<unknown>) => { setError(null); try { await fn(); users.reload(true); } catch (e) { setError((e as Error).message); } };

  const personFields = (p?: Profile) => [
    { name: "full_name", label: "Full name", required: true, defaultValue: p?.full_name },
    ...(p ? [] : [{ name: "email", label: "Email", type: "email" as const, required: true, help: "They sign in with this exact email (Google or email/password, verified) to activate the account." }]),
    { name: "role", label: "Role", type: "select" as const, required: true, defaultValue: p?.role ?? "student", options: ROLES.map((r) => ({ value: r, label: r })) },
    { name: "department_id", label: "Department", type: "select" as const, options: depOpts, defaultValue: p?.department?.id ?? "" },
    { name: "unit_id", label: "Unit", type: "select" as const, options: unitOpts, defaultValue: p?.unit?.id ?? "" },
    { name: "batch_id", label: "SIWES batch (students)", type: "select" as const, options: batchOpts, defaultValue: p?.batch?.id ?? "" },
    { name: "matric_no", label: "Matric number (students)", defaultValue: p?.matric_no ?? "" },
    { name: "phone", label: "Phone (students)", placeholder: "08012345678", defaultValue: p?.phone ?? "" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <input className="input max-w-xs" aria-label="Search people" placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input max-w-[11rem]" aria-label="Filter by role" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">All roles</option>{ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button className="btn-primary ml-auto" onClick={() => setDlg("add")}>Add person</button>
      </div>
      {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{error}</p>}
      <State loading={users.loading} error={users.error} onRetry={users.reload}>
        {users.data?.length === 0 ? <Empty title="No one found" hint="Add people one by one, or import a spreadsheet on the Import tab." /> : (
          <TableWrap>
            <thead><tr><th className="th">Name</th><th className="th">Role</th><th className="th">Department / unit</th><th className="th">Batch</th><th className="th">Status</th><th className="th" /></tr></thead>
            <tbody>{users.data?.map((p) => (
              <tr key={p.id}>
                <td className="td"><b>{p.full_name}</b><br /><span className="text-xs text-ink-faint">{p.email}{p.phone && ` · ${p.phone}`}</span></td>
                <td className="td capitalize">{p.role}</td>
                <td className="td">{p.department?.name ?? "—"}{p.unit && <><br /><span className="text-xs text-ink-faint">{p.unit.name}</span></>}</td>
                <td className="td">{p.role === "student" ? (p.batch?.name ?? <span className="text-warn">Unassigned</span>) : "—"}</td>
                <td className="td"><Badge>{p.is_active ? "Active" : "Inactive"}</Badge></td>
                <td className="td whitespace-nowrap">
                  <button className="btn-secondary btn-sm" onClick={() => setDlg(p)}>Edit</button>{" "}
                  {p.is_active
                    ? <button className="btn-secondary btn-sm" onClick={() => act(() => api(`/api/users/${p.id}`, { method: "DELETE" }))}>Deactivate</button>
                    : <button className="btn-secondary btn-sm" onClick={() => act(() => api(`/api/users/${p.id}`, { method: "PATCH", body: { is_active: true } }))}>Reactivate</button>}{" "}
                  <button className="btn-secondary btn-sm text-bad" onClick={() => { setHardError(null); setHard(p); }}>Delete</button>
                </td>
              </tr>))}</tbody>
          </TableWrap>
        )}
      </State>
      {dlg === "add" && <FormDialog title="Add person" submitLabel="Add" onClose={() => setDlg(null)} fields={personFields()}
        onSubmit={async (v) => { await api("/api/users", { method: "POST", body: v }); users.reload(true); }} />}
      {dlg && dlg !== "add" && <FormDialog title={`Edit ${dlg.full_name}`} onClose={() => setDlg(null)} fields={personFields(dlg)}
        onSubmit={async (v) => { await api(`/api/users/${dlg.id}`, { method: "PATCH", body: v }); users.reload(true); }} />}
      {hard && (
        <Modal title={`Permanently delete ${hard.full_name}?`} onClose={() => setHard(null)}>
          <p className="text-sm text-ink-soft">This removes the person and their attendance and submissions, and deletes their sign-in. Use <b>Deactivate</b> if you only want to block access.</p>
          {hardError && <p className="mt-3 rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{hardError}</p>}
          <div className="mt-5 flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => setHard(null)}>Cancel</button>
            <button className="btn-danger" onClick={async () => {
              try { await api(`/api/users/${hard.id}?hard=true`, { method: "DELETE" }); setHard(null); users.reload(true); }
              catch (e) { setHardError((e as Error).message); }
            }}>Delete permanently</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
