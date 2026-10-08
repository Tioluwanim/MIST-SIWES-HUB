export type Role = "student" | "instructor" | "supervisor" | "admin";

export interface Profile {
  id: number; email: string; full_name: string; role: Role; is_active: boolean;
  department: { id: number; name: string } | null; unit: { id: number; name: string } | null;
  student_id: number | null; batch: { id: number; name: string } | null; matric_no: string | null; institution: string | null; phone?: string | null;
}
export interface Session {
  id: number; title: string; description: string | null; training_class_id: number; class_name: string; program_name: string;
  instructor_id: number | null; instructor_name: string | null; date: string; start_time: string; end_time: string;
  location: string | null; latitude: number; longitude: number; allowed_radius_meters: number;
  attendance_status: "Not Started" | "Open" | "Closed"; my_status: string | null; my_marked_at: string | null;
}
export interface Stats { total: number; present: number; late: number; absent: number; excused: number; rate: number }
export interface Project {
  id: number; title: string; description: string | null; status: string; progress: number; batch_id: number | null;
  start_date: string | null; deadline: string | null; member_count: number;
  members: { student_id: number; name: string; email: string }[]; supervisors: { id: number; name: string }[];
  milestones?: Milestone[];
}
export interface Milestone { id: number; project_id: number; title: string; description: string | null; status: string; due_date: string | null; completed_at: string | null }
export interface Submission {
  id: number; project_id: number; project_title: string; milestone_id: number | null; student_id: number; student_name: string;
  title: string; worked_on: string | null; challenges: string | null; next_steps: string | null; repo_url: string | null;
  project_url: string | null; attachments: { name: string; url: string }[]; review_status: string; feedback: string | null;
  reviewed_at: string | null; created_at: string | null;
}
export interface Announcement { id: number; title: string; message: string; audience: string; created_at: string | null }
export interface Option { value: string | number; label: string }
