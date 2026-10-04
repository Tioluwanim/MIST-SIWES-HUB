"use client";
import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { fmtTime } from "@/lib/format";
import type { Session } from "@/lib/types";
import { Badge } from "../ui";
import { QRScanner } from "./QRScanner";

export const QR_PREFIX = "MISTSIWES:";
type Step = "idle" | "scanning" | "locating" | "submitting" | "done" | "error";

function getPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) return reject(new Error("This browser does not support location."));
    navigator.geolocation.getCurrentPosition(resolve, (err) => {
      reject(new Error(err.code === err.PERMISSION_DENIED
        ? "Location permission is blocked. Allow location for this site in your browser settings, then scan again."
        : err.code === err.TIMEOUT ? "Could not get your location in time. Move near a window or outdoors and try again."
        : "Your location is unavailable right now."));
    }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
  });
}

export function ScanFlow({ onMarked }: { onMarked?: () => void }) {
  const [step, setStep] = useState<Step>("idle");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<{ status: string; distance_meters: number; session: Session } | null>(null);
  const [manual, setManual] = useState("");

  const submit = useCallback(async (raw: string) => {
    const token = raw.startsWith(QR_PREFIX) ? raw.slice(QR_PREFIX.length) : null;
    if (!token) { setStep("error"); setMessage("That is not a MIST attendance code."); return; }
    try {
      setStep("locating");
      const pos = await getPosition();
      setStep("submitting");
      const r = await api<{ status: string; distance_meters: number; session: Session }>("/api/attendance/scan", {
        method: "POST", body: { token, latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy },
      });
      setResult(r); setStep("done"); onMarked?.();
    } catch (e) { setStep("error"); setMessage((e as Error).message); }
  }, [onMarked]);

  const onDecode = useCallback((t: string) => submit(t), [submit]);
  const onCamError = useCallback((m: string) => { setStep("error"); setMessage(m); }, []);

  return (
    <div className="card p-4 sm:p-5">
      {step === "idle" && (
        <div className="text-center">
          <p className="mb-1 text-lg font-bold">Mark your attendance</p>
          <p className="mx-auto mb-4 max-w-sm text-sm text-ink-soft">Scan the QR code on your instructor&apos;s screen. We will ask for your location once to confirm you are at the venue.</p>
          <button className="btn-primary w-full sm:w-auto sm:px-10" onClick={() => { setMessage(""); setStep("scanning"); }}>Scan QR for attendance</button>
        </div>
      )}
      {step === "scanning" && (
        <div>
          <QRScanner onDecode={onDecode} onError={onCamError} />
          <p className="mt-3 text-center text-sm text-ink-soft">Point your camera at the QR code.</p>
          <button className="btn-secondary mt-3 w-full" onClick={() => setStep("idle")}>Cancel</button>
        </div>
      )}
      {(step === "locating" || step === "submitting") && (
        <div className="py-8 text-center" role="status">
          <span className="mx-auto mb-3 block h-8 w-8 animate-spin rounded-full border-4 border-line border-t-brand" />
          <p className="font-semibold">{step === "locating" ? "Getting your location…" : "Verifying attendance…"}</p>
          {step === "locating" && <p className="mt-1 text-sm text-ink-soft">If your phone asks, choose “Allow” for location.</p>}
        </div>
      )}
      {step === "done" && result && (
        <div className="py-4 text-center" role="status">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-ok-soft text-2xl text-ok">✓</div>
          <p className="text-lg font-bold">Attendance recorded</p>
          <p className="mt-1 text-sm text-ink-soft">{result.session.title} · {fmtTime(result.session.start_time)}</p>
          <div className="mt-3 flex items-center justify-center gap-3"><Badge>{result.status}</Badge><span className="text-sm text-ink-soft">{Math.round(result.distance_meters)} m from venue</span></div>
          <button className="btn-secondary mt-5" onClick={() => setStep("idle")}>Done</button>
        </div>
      )}
      {step === "error" && (
        <div className="py-2" role="alert">
          <p className="rounded-md bg-bad-soft p-3 text-sm font-medium text-bad">{message}</p>
          <button className="btn-primary mt-4 w-full" onClick={() => { setMessage(""); setStep("scanning"); }}>Scan again</button>
          <button className="btn-secondary mt-2 w-full" onClick={() => setStep("idle")}>Back</button>
        </div>
      )}
      {(step === "idle" || step === "error") && (
        <details className="mt-5 border-t border-line pt-4 text-sm">
          <summary className="cursor-pointer font-semibold text-ink-soft">Camera not working? Enter the code instead</summary>
          <div className="mt-3 flex gap-2">
            <input className="input" placeholder="Paste the code your instructor reads out" value={manual} onChange={(e) => setManual(e.target.value)} />
            <button className="btn-secondary" disabled={manual.length < 16} onClick={() => submit(manual.startsWith(QR_PREFIX) ? manual : QR_PREFIX + manual.trim())}>Submit</button>
          </div>
        </details>
      )}
    </div>
  );
}
