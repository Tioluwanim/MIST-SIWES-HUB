"use client";
import { useState } from "react";
import { Card, ErrorBox, PageHeader, ProgressBar, RateText, State, TableWrap, Badge } from "@/components/ui";
import { download } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useFetch } from "@/lib/hooks";

type A = Record<string, string | number>;

export default function ReportsPage() {
  const att = useFetch<A[]>("/api/reports/attendance");
  const prj = useFetch<A[]>("/api/reports/projects");
  const [err, setErr] = useState<string | null>(null);
  const dl = (path: string, name: string) => download(path, name).catch((e) => setErr(e.message));
  return (
    <>
      <PageHeader title="Reports" subtitle="Export attendance and project data" />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      <div className="space-y-6">
        <Card title="Attendance report" action={<button className="btn-secondary btn-sm" onClick={() => dl("/api/reports/attendance?format=csv", "attendance-report.csv")}>Download CSV</button>}>
          <State loading={att.loading} error={att.error} onRetry={att.reload}>
            {att.data?.length ? <TableWrap><thead><tr>{["Student", "Department", "Unit", "Sessions", "Present", "Late", "Absent", "Rate"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>{att.data.map((r, i) => <tr key={i}><td className="td font-medium">{r["Student"]}</td><td className="td">{r["Department"] || "—"}</td><td className="td">{r["Unit"] || "—"}</td><td className="td">{r["Sessions"]}</td><td className="td">{r["Present"]}</td><td className="td">{r["Late"]}</td><td className="td">{r["Absent"]}</td><td className="td"><RateText rate={Number(r["Attendance Rate (%)"])} total={Number(r["Sessions"])} /></td></tr>)}</tbody></TableWrap>
              : <p className="text-sm text-ink-soft">No students yet.</p>}
          </State>
        </Card>
        <Card title="Project report" action={<button className="btn-secondary btn-sm" onClick={() => dl("/api/reports/projects?format=csv", "project-report.csv")}>Download CSV</button>}>
          <State loading={prj.loading} error={prj.error} onRetry={prj.reload}>
            {prj.data?.length ? <TableWrap><thead><tr>{["Project", "Students", "Supervisor", "Progress", "Status", "Deadline"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>{prj.data.map((r, i) => <tr key={i}><td className="td font-medium">{r["Project"]}</td><td className="td">{r["Students"] || "—"}</td><td className="td">{r["Supervisors"] || "—"}</td><td className="td w-40"><ProgressBar value={Number(r["Progress (%)"])} /></td><td className="td"><Badge>{String(r["Status"])}</Badge></td><td className="td">{fmtDate(String(r["Deadline"]) || null)}</td></tr>)}</tbody></TableWrap>
              : <p className="text-sm text-ink-soft">No projects yet.</p>}
          </State>
        </Card>
      </div>
    </>
  );
}
