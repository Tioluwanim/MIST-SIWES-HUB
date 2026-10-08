"use client";
import { useState } from "react";
import { AuditPanel } from "@/components/admin/AuditPanel";
import { DataToolsPanel } from "@/components/admin/DataToolsPanel";
import { ImportPanel } from "@/components/admin/ImportPanel";
import { OrgPanel } from "@/components/admin/OrgPanel";
import { PeoplePanel } from "@/components/admin/PeoplePanel";
import { PageHeader } from "@/components/ui";

const TABS = [
  { id: "people", label: "People" }, { id: "org", label: "Batches & units" }, { id: "import", label: "Import data" },
  { id: "tools", label: "Data tools" }, { id: "audit", label: "Audit log" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("people");
  const [rev, setRev] = useState(0); // bump to refresh panels after an import, seed or reset
  return (
    <>
      <PageHeader title="Settings" subtitle="People, data and system tools" />
      <div role="tablist" className="mb-6 flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
            className={`min-h-[44px] shrink-0 border-b-2 px-4 text-sm font-semibold ${tab === t.id ? "border-brand text-brand" : "border-transparent text-ink-soft hover:text-ink"}`}>{t.label}</button>
        ))}
      </div>
      {tab === "people" && <PeoplePanel key={rev} />}
      {tab === "org" && <OrgPanel key={rev} />}
      {tab === "import" && <ImportPanel onImported={() => setRev((r) => r + 1)} />}
      {tab === "tools" && <DataToolsPanel onChanged={() => setRev((r) => r + 1)} />}
      {tab === "audit" && <AuditPanel key={rev} />}
    </>
  );
}
