"use client";
import { Card, PageHeader } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";

export default function ProfilePage() {
  const { profile: p, signOut } = useAuth();
  const rows: [string, string | undefined | null][] = [["Full name", p!.full_name], ["Email", p!.email], ["Role", p!.role], ["Department", p!.department?.name], ["Unit", p!.unit?.name], ["SIWES batch", p!.batch?.name], ["Matric number", p!.matric_no], ["Institution", p!.institution]];
  return (
    <>
      <PageHeader title="Profile" />
      <Card className="max-w-xl"><dl className="divide-y divide-line">{rows.filter(([k, v]) => v || ["Department", "Unit"].includes(k) === false ? v : true).map(([k, v]) => <div key={k} className="flex justify-between gap-4 py-3 text-sm"><dt className="text-ink-soft">{k}</dt><dd className="font-semibold capitalize">{v || "—"}</dd></div>)}</dl>
        <p className="mt-3 text-xs text-ink-faint">Department, unit and batch are assigned by the ministry.</p>
        <button className="btn-secondary mt-4" onClick={signOut}>Sign out</button></Card>
    </>
  );
}
