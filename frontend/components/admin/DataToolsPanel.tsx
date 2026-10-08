"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { Card, ErrorBox, Modal, State } from "../ui";

const SCOPES: Record<string, string> = {
  attendance: "All attendance records and open attendance sessions",
  projects: "All projects, milestones, team assignments and progress updates",
  announcements: "All announcements",
  training: "Programs, classes, sessions, materials, enrolments and attendance",
  students: "All student accounts and their data (staff and admins are kept)",
  all_except_admins: "EVERYTHING except admin accounts: people, training, projects, announcements, batches, departments and units",
};

interface Status { destructive_enabled: boolean; demo_rows: number; totals: { students: number; users: number } }
interface SeedResult { created: number; skipped: number; tables: Record<string, number>; warnings: string[] }

export function DataToolsPanel({ onChanged }: { onChanged?: () => void }) {
  const status = useFetch<Status>("/api/admin/status");
  const [seed, setSeed] = useState({ include_demo: true, instructor_email: "", supervisor_email: "" });
  const [seedResult, setSeedResult] = useState<SeedResult | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [scope, setScope] = useState("attendance");
  const [typed, setTyped] = useState("");
  const [confirmDemo, setConfirmDemo] = useState(false);
  const off = status.data ? !status.data.destructive_enabled : true;

  async function run(fn: () => Promise<string>) {
    setBusy(true); setMsg(null);
    try { setMsg({ ok: true, text: await fn() }); status.reload(true); onChanged?.(); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(false); }
  }

  return (
    <State loading={status.loading} error={status.error} onRetry={status.reload}>
      <div className="space-y-6">
        {msg && (msg.ok ? <p className="rounded-md bg-ok-soft p-3 text-sm text-ok" role="status">{msg.text}</p> : <ErrorBox message={msg.text} />)}

        <Card title="Seed demo data">
          <p className="mb-3 text-sm text-ink-soft">Adds a sample batch, departments, classes, sessions, attendance, a project and announcements so you can try the platform. Demo rows are tagged, so they can be removed later without touching real data. Running it twice does nothing the second time.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className="label" htmlFor="si">Instructor email (optional)</label><input id="si" type="email" className="input" placeholder="a real address you can sign in with" value={seed.instructor_email} onChange={(e) => setSeed({ ...seed, instructor_email: e.target.value })} /></div>
            <div><label className="label" htmlFor="ss">Supervisor email (optional)</label><input id="ss" type="email" className="input" value={seed.supervisor_email} onChange={(e) => setSeed({ ...seed, supervisor_email: e.target.value })} /></div>
          </div>
          <button className="btn-primary mt-4" disabled={busy} onClick={() => run(async () => {
            const r = await api<SeedResult>("/api/admin/seed", { method: "POST", body: { include_demo: seed.include_demo, instructor_email: seed.instructor_email || undefined, supervisor_email: seed.supervisor_email || undefined } });
            setSeedResult(r);
            return r.created ? `Created ${r.created} demo records.` : (r.warnings[0] ?? "Nothing to add.");
          })}>Seed demo data</button>
          {seedResult?.warnings.length ? <ul className="mt-3 list-disc pl-5 text-sm text-warn">{seedResult.warnings.map((w) => <li key={w}>{w}</li>)}</ul> : null}
          {seedResult && seedResult.created > 0 && <p className="mt-3 text-xs text-ink-faint">{Object.entries(seedResult.tables).map(([k, v]) => `${v} ${k}`).join(" · ")}</p>}
        </Card>

        <Card title="Remove demo data">
          <p className="text-sm text-ink-soft">Deletes only the sample records created by the seed. People and data you added or imported are never touched, and neither are admin accounts. Demo records currently present: <b>{status.data?.demo_rows ?? 0}</b>.</p>
          <button className="btn-secondary mt-4" disabled={busy || off || !status.data?.demo_rows} onClick={() => setConfirmDemo(true)}>Remove demo data</button>
        </Card>

        <section className="rounded-lg border-2 border-bad/40 p-4 sm:p-5">
          <h2 className="text-[15px] font-bold text-bad">Danger zone</h2>
          {off && <p className="mt-2 rounded-md bg-warn-soft p-3 text-sm text-warn">Deleting and resetting are switched off on this server. To enable them, set <code>ALLOW_DESTRUCTIVE_ADMIN=true</code> in the backend environment, redeploy, and switch it off again afterwards.</p>}
          <div className="mt-3 grid gap-3">
            <div><label className="label" htmlFor="sc">What to reset</label>
              <select id="sc" className="input" value={scope} onChange={(e) => { setScope(e.target.value); setTyped(""); }}>{Object.keys(SCOPES).map((k) => <option key={k} value={k}>{k.replace(/_/g, " ")}</option>)}</select>
              <p className="mt-1 text-sm text-ink-soft">This will delete: {SCOPES[scope]}.</p></div>
            <div><label className="label" htmlFor="ty">Type RESET to confirm</label><input id="ty" className="input max-w-xs" autoComplete="off" value={typed} onChange={(e) => setTyped(e.target.value)} /></div>
          </div>
          <button className="btn-danger mt-4" disabled={busy || off || typed !== "RESET"} onClick={() => run(async () => {
            const r = await api<{ deleted: number }>("/api/admin/reset", { method: "POST", body: { scope, confirm: typed } });
            setTyped("");
            return `Reset complete. ${r.deleted} records removed.`;
          })}>Reset {scope.replace(/_/g, " ")}</button>
          <p className="mt-2 text-xs text-ink-faint">Everything happens in one step: if anything fails, nothing is changed. Your account is never deleted.</p>
        </section>
      </div>
      {confirmDemo && (
        <Modal title="Remove all demo data?" onClose={() => setConfirmDemo(false)}>
          <p className="text-sm text-ink-soft">{status.data?.demo_rows} demo records will be deleted. Real and imported data is kept.</p>
          <div className="mt-5 flex justify-end gap-2"><button className="btn-secondary" onClick={() => setConfirmDemo(false)}>Cancel</button>
            <button className="btn-danger" onClick={() => { setConfirmDemo(false); run(async () => { const r = await api<{ deleted: number }>("/api/admin/demo-data", { method: "DELETE" }); return `Removed ${r.deleted} demo records.`; }); }}>Remove</button></div>
        </Modal>
      )}
    </State>
  );
}
