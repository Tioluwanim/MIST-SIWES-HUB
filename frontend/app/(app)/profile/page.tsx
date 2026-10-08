"use client";
import { DepartmentUnitForm } from "@/components/DepartmentUnitForm";
import { Card, PageHeader } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";

export default function ProfilePage() {
  const { profile: p, signOut } = useAuth();
  const student = p!.role === "student";
  const rows: [string, string | undefined | null][] = [
    ["Full name", p!.full_name], ["Email", p!.email], ["Role", p!.role],
    ...(student ? [] : ([["Department", p!.department?.name], ["Unit", p!.unit?.name]] as [string, string | undefined][])),
    ["SIWES batch", p!.batch?.name], ["Matric number", p!.matric_no], ["Institution", p!.institution], ["Phone", p!.phone],
  ];
  return (
    <>
      <PageHeader title="Profile" />
      <div className="grid max-w-3xl gap-6">
        <Card>
          <dl className="divide-y divide-line">{rows.map(([k, v]) => <div key={k} className="flex justify-between gap-4 py-3 text-sm"><dt className="text-ink-soft">{k}</dt><dd className="text-right font-semibold capitalize">{v || "—"}</dd></div>)}</dl>
          <p className="mt-3 text-xs text-ink-faint">Batch and other details are assigned by the ministry.</p>
        </Card>
        {student && <Card title="Department and unit"><p className="mb-4 text-sm text-ink-soft">Where you are placed for your SIWES. Pick your department first, then your unit.</p><DepartmentUnitForm /></Card>}
        <div><button className="btn-secondary" onClick={signOut}>Sign out</button></div>
      </div>
    </>
  );
}
