"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { Modal } from "../ui";

// Lagos State Secretariat, Alausa (Ikeja). Instructors can replace it with their current position.
const DEFAULT = { lat: "6.6186", lng: "3.3569" };

export function SessionForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const classes = useFetch<{ id: number; name: string; program_name: string }[]>("/api/training/classes");
  const [v, setV] = useState({ training_class_id: "", title: "", description: "", date: new Date().toISOString().slice(0, 10), start_time: "10:00", end_time: "12:00", location: "MIST Training Hall, Alausa Secretariat", latitude: DEFAULT.lat, longitude: DEFAULT.lng, allowed_radius_meters: "100" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [locMsg, setLocMsg] = useState("");
  const set = (k: string, val: string) => setV((s) => ({ ...s, [k]: val }));

  function useHere() {
    setLocMsg("Locating…");
    navigator.geolocation?.getCurrentPosition(
      (p) => { set("latitude", p.coords.latitude.toFixed(6)); set("longitude", p.coords.longitude.toFixed(6)); setLocMsg(`Set (±${Math.round(p.coords.accuracy)} m)`); },
      () => setLocMsg("Location unavailable. Enter coordinates manually."), { enableHighAccuracy: true, timeout: 15000 });
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      await api("/api/sessions", { method: "POST", body: {
        training_class_id: Number(v.training_class_id), title: v.title, description: v.description || undefined, date: v.date,
        start_time: v.start_time + ":00", end_time: v.end_time + ":00", location: v.location || undefined,
        latitude: Number(v.latitude), longitude: Number(v.longitude), allowed_radius_meters: Number(v.allowed_radius_meters) } });
      onSaved(); onClose();
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  return (
    <Modal title="New training session" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <div><label className="label" htmlFor="cls">Class *</label>
          <select id="cls" required className="input" value={v.training_class_id} onChange={(e) => set("training_class_id", e.target.value)}>
            <option value="">Select class…</option>{classes.data?.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.program_name})</option>)}
          </select></div>
        <div><label className="label" htmlFor="t">Title *</label><input id="t" required minLength={2} className="input" value={v.title} onChange={(e) => set("title", e.target.value)} /></div>
        <div><label className="label" htmlFor="d">Description</label><textarea id="d" className="input min-h-[72px] py-2" value={v.description} onChange={(e) => set("description", e.target.value)} /></div>
        <div className="grid grid-cols-3 gap-3">
          <div><label className="label" htmlFor="dt">Date *</label><input id="dt" type="date" required className="input" value={v.date} onChange={(e) => set("date", e.target.value)} /></div>
          <div><label className="label" htmlFor="st">Starts *</label><input id="st" type="time" required className="input" value={v.start_time} onChange={(e) => set("start_time", e.target.value)} /></div>
          <div><label className="label" htmlFor="et">Ends *</label><input id="et" type="time" required className="input" value={v.end_time} onChange={(e) => set("end_time", e.target.value)} /></div>
        </div>
        <div><label className="label" htmlFor="loc">Venue</label><input id="loc" className="input" value={v.location} onChange={(e) => set("location", e.target.value)} /></div>
        <fieldset className="rounded-md border border-line p-3">
          <legend className="px-1 text-[13px] font-semibold">Attendance location</legend>
          <div className="grid grid-cols-3 gap-3">
            <div><label className="label" htmlFor="lat">Latitude</label><input id="lat" required type="number" step="any" className="input" value={v.latitude} onChange={(e) => set("latitude", e.target.value)} /></div>
            <div><label className="label" htmlFor="lng">Longitude</label><input id="lng" required type="number" step="any" className="input" value={v.longitude} onChange={(e) => set("longitude", e.target.value)} /></div>
            <div><label className="label" htmlFor="rad">Radius (m)</label><input id="rad" required type="number" min={10} max={5000} className="input" value={v.allowed_radius_meters} onChange={(e) => set("allowed_radius_meters", e.target.value)} /></div>
          </div>
          <div className="mt-2 flex items-center gap-3"><button type="button" className="btn-secondary btn-sm" onClick={useHere}>Use my current location</button><span className="text-xs text-ink-soft">{locMsg}</span></div>
        </fieldset>
        {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Create session"}</button></div>
      </form>
    </Modal>
  );
}
