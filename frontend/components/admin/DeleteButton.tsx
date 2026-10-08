"use client";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Modal } from "../ui";

/**
 * Delete with a confirmation step. If the server reports dependants (409) the message says exactly what
 * would be affected and offers "Delete anyway" (force). A 403 explains that destructive actions are switched off.
 */
export function DeleteButton({ path, noun, label = "Delete", onDone, className = "btn-secondary btn-sm text-bad" }: {
  path: string; noun: string; label?: string; onDone: () => void; className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);

  async function run(force: boolean) {
    setBusy(true); setError(null);
    try {
      await api(`${path}${force ? (path.includes("?") ? "&" : "?") + "force=true" : ""}`, { method: "DELETE" });
      setOpen(false); setConflict(false); onDone();
    } catch (e) {
      const err = e as ApiError;
      setConflict(err.status === 409 && !force);
      setError(err.message);
    } finally { setBusy(false); }
  }
  const close = () => { setOpen(false); setError(null); setConflict(false); };
  return (
    <>
      <button type="button" className={className} onClick={() => setOpen(true)}>{label}</button>
      {open && (
        <Modal title={`Delete this ${noun}?`} onClose={close}>
          <p className="text-sm text-ink-soft">{conflict || error ? null : "This cannot be undone."}</p>
          {error && <p className={`rounded-md p-3 text-sm ${conflict ? "bg-warn-soft text-warn" : "bg-bad-soft text-bad"}`} role="alert">{error}</p>}
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <button className="btn-secondary" onClick={close}>Cancel</button>
            {conflict
              ? <button className="btn-danger" disabled={busy} onClick={() => run(true)}>{busy ? "Deleting…" : "Delete anyway"}</button>
              : !error && <button className="btn-danger" disabled={busy} onClick={() => run(false)}>{busy ? "Deleting…" : "Delete"}</button>}
          </div>
        </Modal>
      )}
    </>
  );
}
