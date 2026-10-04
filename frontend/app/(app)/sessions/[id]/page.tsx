"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { LiveAttendance } from "@/components/attendance/LiveAttendance";
import { PageHeader } from "@/components/ui";

export default function SessionLive() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <PageHeader title="Session attendance" actions={<Link href="/attendance" className="btn-secondary btn-sm">Back</Link>} />
      <LiveAttendance sessionId={Number(id)} />
    </>
  );
}
