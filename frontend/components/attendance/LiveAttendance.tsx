"use client";
import { QRCodeSVG } from "qrcode.react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { fmtClock, fmtDate, fmtTime } from "@/lib/format";
import type { Session } from "@/lib/types";
import { Badge, Card, ErrorBox, State, Stat, TableWrap } from "../ui";
import { QR_PREFIX } from "./ScanFlow";

interface Live {
  session: Session; is_active: boolean; total: number; counts: Record<string, number>;
  roster: { student_id: number; name: string; status: string; method: string | null; marked_at: string | null; distance_meters: number | null }[];
}
interface Tok { token: string; expires_at: string; ttl_seconds: number }

export function LiveAttendance({ sessionId }: { sessionId: number }) {
  const live = useFetch<Live>(`/api/attendance/sessions/${sessionId}/live`);
  const [tok, setTok] = useState<Tok | null>(null);
  const [left, setLeft] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const tokRef = useRef<Tok | null>(null);
  tokRef.current = tok;
  const active = live.data?.is_active ?? false;

  const rotate = useCallback(async (path: "start" | "refresh") => {
    try { setTok(await api<Tok>(`/api/attendance/sessions/${sessionId}/${path}`, { method: "POST" })); setErr(null); }
    catch (e) { setErr((e as Error).message); }
  }, [sessionId]);

  // poll roster every 4s while open
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => live.reload(true), 4000);
    return () => clearInterval(id);
  }, [active, live]);

  // keep the QR fresh: get a code when the page opens on an already-open session, then rotate before expiry
  useEffect(() => {
    if (!active) { setTok(null); return; }
    if (!tokRef.current) rotate("refresh");
    const id = setInterval(() => {
      const t = tokRef.current;
      const remaining = t ? (new Date(t.expires_at).getTime() - Date.now()) / 1000 : 0;
      setLeft(Math.max(0, Math.round(remaining)));
      if (!t || remaining < 8) rotate("refresh");
    }, 1000);
    return () => clearInterval(id);
  }, [active, rotate]);

  async function toggle() {
    setBusy(true); setErr(null);
    try {
      if (active) { await api(`/api/attendance/sessions/${sessionId}/stop`, { method: "POST" }); setTok(null); }
      else setTok(await api<Tok>(`/api/attendance/sessions/${sessionId}/start`, { method: "POST" }));
      await live.reload(true);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function mark(student_id: number, status: string) {
    try { await api("/api/attendance/manual", { method: "POST", body: { session_id: sessionId, student_id, status } }); await live.reload(true); }
    catch (e) { setErr((e as Error).message); }
  }

  return (
    <State loading={live.loading} error={live.error} onRetry={live.reload}>
      {live.data && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-3 text-sm text-ink-soft">
            <Badge>{live.data.session.attendance_status}</Badge>
            <span>{fmtDate(live.data.session.date)} · {fmtTime(live.data.session.start_time)}–{fmtTime(live.data.session.end_time)}</span>
            <span>{live.data.session.location ?? "No venue set"} · radius {live.data.session.allowed_radius_meters} m</span>
          </div>
          {err && <ErrorBox message={err} />}
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            <Card title="Attendance code">
              {active && tok ? (
                <div className="text-center">
                  <div className="mx-auto inline-block rounded-lg border border-line bg-white p-3"><QRCodeSVG value={QR_PREFIX + tok.token} size={240} level="M" /></div>
                  <p className="mt-3 text-sm text-ink-soft">New code in <b className="tabular-nums text-ink">{left}s</b>. Students must be at the venue.</p>
                  <details className="mt-2 text-left text-xs text-ink-faint"><summary className="cursor-pointer">Show code as text</summary><code className="mt-1 block break-all">{tok.token}</code></details>
                </div>
              ) : <p className="py-6 text-center text-sm text-ink-soft">{active ? "Generating code…" : live.data.session.attendance_status === "Closed" ? "Attendance is closed. Reopen it to scan again." : "Start attendance to show the QR code."}</p>}
              <button className={`${active ? "btn-danger" : "btn-primary"} mt-4 w-full`} disabled={busy} onClick={toggle}>
                {active ? "Stop attendance" : live.data.session.attendance_status === "Closed" ? "Reopen attendance" : "Start attendance"}
              </button>
              {active && <p className="mt-2 text-xs text-ink-faint">Stopping marks everyone who has not checked in as Absent.</p>}
            </Card>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Stat label="Present" value={live.data.counts.Present} /><Stat label="Late" value={live.data.counts.Late} />
                <Stat label="Absent" value={live.data.counts.Absent} /><Stat label="Waiting" value={live.data.counts.Pending} hint={`of ${live.data.total} enrolled`} />
              </div>
              <TableWrap>
                <thead><tr><th className="th">Student</th><th className="th">Status</th><th className="th">Time</th><th className="th">Distance</th><th className="th">Set status</th></tr></thead>
                <tbody>{live.data.roster.map((r) => (
                  <tr key={r.student_id}>
                    <td className="td font-medium">{r.name}</td>
                    <td className="td"><Badge>{r.status}</Badge></td>
                    <td className="td">{r.status === "Pending" || r.status === "Absent" ? "—" : `${fmtClock(r.marked_at)}${r.method === "Manual" ? " (manual)" : ""}`}</td>
                    <td className="td">{r.distance_meters != null ? `${Math.round(r.distance_meters)} m` : "—"}</td>
                    <td className="td"><select aria-label={`Set status for ${r.name}`} className="input !min-h-[34px] !py-0" value="" onChange={(e) => e.target.value && mark(r.student_id, e.target.value)}>
                      <option value="">Change…</option>{["Present", "Late", "Absent", "Excused"].map((s) => <option key={s}>{s}</option>)}</select></td>
                  </tr>
                ))}</tbody>
              </TableWrap>
            </div>
          </div>
        </div>
      )}
    </State>
  );
}
