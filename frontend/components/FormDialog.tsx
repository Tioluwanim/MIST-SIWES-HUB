"use client";
import { useState } from "react";
import { Modal } from "./ui";
import type { Option } from "@/lib/types";

export interface FieldDef {
  name: string; label: string;
  type?: "text" | "email" | "textarea" | "number" | "date" | "time" | "select" | "multiselect" | "checkbox" | "url";
  options?: Option[]; required?: boolean; placeholder?: string; defaultValue?: any; help?: string; step?: string;
}

export function FormDialog({ title, fields, submitLabel = "Save", onSubmit, onClose }: {
  title: string; fields: FieldDef[]; submitLabel?: string; onClose: () => void;
  onSubmit: (values: Record<string, any>) => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, any>>(() => Object.fromEntries(fields.map((f) => [f.name, f.defaultValue ?? (f.type === "multiselect" ? [] : f.type === "checkbox" ? false : "")])));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: any) => setValues((s) => ({ ...s, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const out: Record<string, any> = {};
    for (const f of fields) {
      const v = values[f.name];
      if (f.type === "number" || (f.type === "select" && f.options?.some((o) => typeof o.value === "number"))) out[f.name] = v === "" ? undefined : Number(v);
      else if (f.type === "multiselect") out[f.name] = (v as any[]).map(Number);
      else out[f.name] = v === "" ? undefined : v;
    }
    try {
      await onSubmit(out);
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        {fields.map((f) => (
          <div key={f.name}>
            {f.type === "checkbox" ? (
              <label className="flex min-h-[44px] items-center gap-3 text-sm">
                <input type="checkbox" className="h-5 w-5 accent-brand" checked={!!values[f.name]} onChange={(e) => set(f.name, e.target.checked)} />
                {f.label}
              </label>
            ) : (
              <>
                <label className="label" htmlFor={f.name}>{f.label}{f.required && <span className="text-bad"> *</span>}</label>
                {f.type === "textarea" ? (
                  <textarea id={f.name} className="input min-h-[96px] py-2" required={f.required} placeholder={f.placeholder} value={values[f.name]} onChange={(e) => set(f.name, e.target.value)} />
                ) : f.type === "select" ? (
                  <select id={f.name} className="input" required={f.required} value={values[f.name]} onChange={(e) => set(f.name, e.target.value)}>
                    <option value="">{f.required ? "Select…" : "None"}</option>
                    {f.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                ) : f.type === "multiselect" ? (
                  <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-line p-2">
                    {f.options?.length ? f.options.map((o) => (
                      <label key={o.value} className="flex min-h-[36px] items-center gap-2 text-sm">
                        <input type="checkbox" className="h-4 w-4 accent-brand" checked={values[f.name].includes(o.value)}
                          onChange={(e) => set(f.name, e.target.checked ? [...values[f.name], o.value] : values[f.name].filter((x: any) => x !== o.value))} />
                        {o.label}
                      </label>
                    )) : <p className="text-sm text-ink-faint">Nothing to choose yet.</p>}
                  </div>
                ) : (
                  <input id={f.name} className="input" type={f.type ?? "text"} step={f.step} required={f.required} placeholder={f.placeholder} value={values[f.name]} onChange={(e) => set(f.name, e.target.value)} />
                )}
                {f.help && <p className="mt-1 text-xs text-ink-faint">{f.help}</p>}
              </>
            )}
          </div>
        ))}
        {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={busy}>{busy ? "Saving…" : submitLabel}</button>
        </div>
      </form>
    </Modal>
  );
}
