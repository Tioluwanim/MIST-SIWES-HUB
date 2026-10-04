"use client";
import { useEffect, useRef, useState } from "react";

/** Camera QR scanner (html5-qrcode, loaded lazily so it never blocks the initial page). */
export function QRScanner({ onDecode, onError }: { onDecode: (text: string) => void; onError: (msg: string) => void }) {
  const ref = useRef<any>(null);
  const done = useRef(false);
  const [starting, setStarting] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { Html5Qrcode } = await import("html5-qrcode");
        if (cancelled) return;
        const scanner = new Html5Qrcode("qr-reader", { verbose: false });
        ref.current = scanner;
        await scanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: (w, h) => { const s = Math.floor(Math.min(w, h) * 0.75); return { width: s, height: s }; } },
          (text) => { if (!done.current) { done.current = true; onDecode(text); } },
          () => {},
        );
        setStarting(false);
      } catch (e: any) {
        const msg = String(e?.message ?? e);
        onError(/permission|denied|NotAllowed/i.test(msg)
          ? "Camera access was blocked. Allow camera permission for this site in your browser settings, then try again."
          : /secure|https/i.test(msg) ? "Camera needs a secure (HTTPS) connection."
          : "Could not start the camera on this device.");
      }
    })();
    return () => {
      cancelled = true;
      const s = ref.current;
      if (s) s.stop().then(() => s.clear()).catch(() => {});
    };
  }, [onDecode, onError]);

  return (
    <div>
      <div id="qr-reader" className="overflow-hidden rounded-lg bg-ink" style={{ minHeight: 280 }} />
      {starting && <p className="mt-2 text-center text-sm text-ink-soft">Starting camera…</p>}
    </div>
  );
}
