"use client";
import { PageHeader } from "@/components/ui";
import { SessionsPanel } from "@/components/training/SessionsPanel";

export default function SessionsPage() {
  return (<><PageHeader title="Sessions" subtitle="Schedule sessions and run attendance" /><SessionsPanel /></>);
}
