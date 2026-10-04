"use client";
import { useState } from "react";
import { SubmissionCard } from "@/components/projects/SubmissionCard";
import { Empty, PageHeader, State } from "@/components/ui";
import { useFetch } from "@/lib/hooks";
import type { Submission } from "@/lib/types";

export default function SubmissionsPage() {
  const [filter, setFilter] = useState("Pending");
  const { data, loading, error, reload } = useFetch<Submission[]>(`/api/submissions${filter ? `?review_status=${encodeURIComponent(filter)}` : ""}`);
  return (
    <>
      <PageHeader title="Submissions" subtitle="Review progress updates from your students" actions={
        <select aria-label="Filter" className="input !w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="Pending">Awaiting review</option><option value="Approved">Approved</option><option value="Changes Requested">Changes requested</option><option value="">All</option></select>} />
      <State loading={loading} error={error} onRetry={reload}>
        {data?.length ? <div className="space-y-3">{data.map((s) => <SubmissionCard key={s.id} s={s} showProject canReview onChanged={() => reload(true)} />)}</div> : <Empty title="Nothing here" hint="No submissions match this filter." />}
      </State>
    </>
  );
}
