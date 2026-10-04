"use client";
import { AdminDashboard } from "@/components/dashboards/AdminDashboard";
import { InstructorDashboard, SupervisorDashboard } from "@/components/dashboards/StaffDashboards";
import { StudentDashboard } from "@/components/dashboards/StudentDashboard";
import { useAuth } from "@/context/AuthContext";

export default function Dashboard() {
  const { profile } = useAuth();
  switch (profile!.role) {
    case "admin": return <AdminDashboard />;
    case "instructor": return <InstructorDashboard />;
    case "supervisor": return <SupervisorDashboard />;
    default: return <StudentDashboard />;
  }
}
