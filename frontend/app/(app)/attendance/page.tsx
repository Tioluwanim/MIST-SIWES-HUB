"use client";
import { StaffOverview } from "@/components/attendance/StaffOverview";
import { StudentAttendance } from "@/components/attendance/StudentAttendance";
import { PageHeader } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";

export default function AttendancePage() {
  const { profile } = useAuth();
  const student = profile!.role === "student";
  return (
    <>
      <PageHeader title="Attendance" subtitle={student ? "Scan in to your training sessions" : "Monitor attendance across training sessions"} />
      {student ? <StudentAttendance /> : <StaffOverview />}
    </>
  );
}
