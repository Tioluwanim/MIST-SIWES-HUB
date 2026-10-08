"use client";
import { useRef, useState } from "react";
import { ApiError, download, uploadFile } from "@/lib/api";
import { Card } from "../ui";

interface Err { sheet: string; row: number; column: string; message: string }
interface Sheet { sheet: string; created: number; updated: number; skipped: number; errors: Err[] }
interface Result { sheets: Sheet[]; total_errors: number; dry_run: boolean }

const CSV_TYPES = ["students", "instructors", "supervisors", "admins", "departments", "units", "batches", "programs", "classes", "sessions", "projects"];

export function ImportPanel({ onImported }: { onImported?: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [csvType, setCsvType] = useState("students");
  const [preview, setPreview] = useState<Result | null>(null);
  const [done, setDone] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const isCsv = !!file && file.name.toLowerCase().endsWith(".csv");

  async function run(f: File, flags: string, final: boolean, csv = f.name.toLowerCase().endsWith(".csv")) {
    setBusy(true); setError(null);
    try {
      const r = await uploadFile<Result>(`/api/admin/import?${flags}${csv ? `&type=${csvType}` : ""}`, f);
      if (final) { setDone(r); setPreview(null); setFile(null); if (input.current) input.current.value = ""; onImported?.(); } else setPreview(r);
    } catch (e) {
      const err = e as ApiError;
      const detail = err.detail as { sheets?: Sheet[]; total_errors?: number } | undefined;
      if (detail?.sheets) setPreview({ sheets: detail.sheets, total_errors: detail.total_errors ?? 0, dry_run: false });
      setError(err.message);
    } finally { setBusy(false); }
  }
  const pick = (f: File | null) => { setFile(f); setPreview(null); setDone(null); setError(null); if (f) run(f, "dry_run=true", false); };
  const errors = preview?.sheets.flatMap((s) => s.errors) ?? [];

  return (
    <div className="space-y-6">
      <Card title="1. Choose a spreadsheet" action={<button className="btn-secondary btn-sm" onClick={() => download("/api/admin/import/template", "siwes-import-template.xlsx").catch((e) => setError(e.message))}>Download template</button>}>
        <p className="mb-3 text-sm text-ink-soft">Upload an Excel workbook (.xlsx) built from the template, or a single-sheet CSV. Nothing is saved until you confirm in step 2. Re-uploading the same file never creates duplicates.</p>
        <div className="flex flex-wrap items-center gap-3">
          <input ref={input} type="file" accept=".xlsx,.csv" aria-label="Spreadsheet file" className="input max-w-md py-2" onChange={(e) => pick(e.target.files?.[0] ?? null)} />
          {isCsv && (
            <select className="input max-w-[12rem]" aria-label="What are the CSV rows?" value={csvType} onChange={(e) => setCsvType(e.target.value)} onBlur={() => file && run(file, "dry_run=true", false)}>
              {CSV_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          )}
          {isCsv && <button className="btn-secondary btn-sm" disabled={busy} onClick={() => file && run(file, "dry_run=true", false)}>Re-check</button>}
        </div>
        {busy && <p className="mt-3 text-sm text-ink-soft" role="status">Working…</p>}
        {error && <p className="mt-3 rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{error}</p>}
      </Card>

      {preview && (
        <Card title="2. Review and import">
          <div className="overflow-x-auto"><table className="w-full min-w-[420px] border-collapse">
            <thead><tr><th className="th">Sheet</th><th className="th">Will create</th><th className="th">Will update</th><th className="th">Skipped</th><th className="th">Errors</th></tr></thead>
            <tbody>{preview.sheets.map((s) => <tr key={s.sheet}><td className="td font-medium">{s.sheet}</td><td className="td">{s.created}</td><td className="td">{s.updated}</td><td className="td">{s.skipped}</td><td className={`td ${s.errors.length ? "font-semibold text-bad" : ""}`}>{s.errors.length}</td></tr>)}</tbody>
          </table></div>
          {errors.length > 0 && (
            <div className="mt-4 max-h-64 overflow-auto rounded-md border border-line">
              <table className="w-full border-collapse text-sm"><thead><tr><th className="th">Sheet</th><th className="th">Row</th><th className="th">Problem</th></tr></thead>
                <tbody>{errors.map((e, i) => <tr key={i}><td className="td">{e.sheet}</td><td className="td">{e.row}</td><td className="td">{e.column ? `${e.column}: ` : ""}{e.message}</td></tr>)}</tbody></table>
            </div>
          )}
          {preview.total_errors > errors.length && <p className="mt-2 text-xs text-ink-faint">Showing the first {errors.length} of {preview.total_errors} errors.</p>}
          <div className="mt-5 flex flex-wrap gap-2">
            <button className="btn-primary" disabled={busy || !file || preview.total_errors > 0} onClick={() => file && run(file, "dry_run=false", true)}>Import everything</button>
            <button className="btn-secondary" disabled={busy || !file || preview.sheets.every((s) => s.created + s.updated === 0)} onClick={() => file && run(file, "skip_invalid=true", true)}>Import valid rows only</button>
          </div>
          {preview.total_errors > 0 && <p className="mt-2 text-xs text-ink-faint">Fix the rows above and re-upload, or import only the valid rows. Skipped rows are not saved.</p>}
        </Card>
      )}

      {done && (
        <Card title="Import complete">
          <ul className="space-y-1 text-sm">{done.sheets.map((s) => <li key={s.sheet}><b>{s.sheet}</b>: {s.created} created, {s.updated} updated{s.skipped ? `, ${s.skipped} skipped` : ""}</li>)}</ul>
          <p className="mt-3 text-sm text-ink-soft">People you imported are linked automatically the first time they sign in with the same verified email.</p>
        </Card>
      )}
    </div>
  );
}
