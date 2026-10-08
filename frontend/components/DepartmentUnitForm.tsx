"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { Spinner } from "./ui";

/** Lets a student choose their own department and unit. The server takes the student from their login. */
export function DepartmentUnitForm({ onSaved }: { onSaved?: () => void }) {
  const { profile, refreshProfile } = useAuth();
  const deps = useFetch<{ id: number; name: string }[]>("/api/departments");
  const units = useFetch<{ id: number; name: string; department_id: number }[]>("/api/units");
  const [dep, setDep] = useState<string>(String(profile?.department?.id ?? ""));
  const [unit, setUnit] = useState<string>(String(profile?.unit?.id ?? ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => { setDep(String(profile?.department?.id ?? "")); setUnit(String(profile?.unit?.id ?? "")); }, [profile?.department?.id, profile?.unit?.id]);

  if (deps.loading || units.loading) return <Spinner />;
  if (deps.error) return <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{deps.error}</p>;
  if (!deps.data?.length) return <p className="rounded-md bg-surface p-3 text-sm text-ink-soft">The ministry has not set up departments yet. Please check back soon.</p>;

  const options = (units.data ?? []).filter((u) => String(u.department_id) === dep);
  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null); setSaved(false);
    try {
      await api("/api/students/me/profile", { method: "PATCH", body: { department_id: Number(dep), unit_id: Number(unit) } });
      await refreshProfile();
      setSaved(true); onSaved?.();
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={save} className="space-y-4">
      <div><label className="label" htmlFor="my-dep">Department</label>
        <select id="my-dep" required className="input" value={dep} onChange={(e) => { setDep(e.target.value); setUnit(""); setSaved(false); }}>
          <option value="">Select your department…</option>{deps.data.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
      <div><label className="label" htmlFor="my-unit">Unit</label>
        <select id="my-unit" required className="input" disabled={!dep} value={unit} onChange={(e) => { setUnit(e.target.value); setSaved(false); }}>
          <option value="">{dep ? (options.length ? "Select your unit…" : "No units in this department yet") : "Choose a department first"}</option>
          {options.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</select></div>
      {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{error}</p>}
      {saved && <p className="rounded-md bg-ok-soft p-3 text-sm text-ok" role="status">Saved. Your department and unit are updated.</p>}
      <button className="btn-primary w-full sm:w-auto" disabled={busy || !dep || !unit}>{busy ? "Saving…" : "Save"}</button>
    </form>
  );
}
