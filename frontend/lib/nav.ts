import type { Role } from "./types";

export interface NavItem { href: string; label: string; icon: string; primary?: boolean }

export const NAV: Record<Role, NavItem[]> = {
  student: [
    { href: "/dashboard", label: "Dashboard", icon: "home", primary: true },
    { href: "/attendance", label: "Attendance", icon: "scan", primary: true },
    { href: "/training", label: "Training", icon: "book", primary: true },
    { href: "/projects", label: "Projects", icon: "folder", primary: true },
    { href: "/announcements", label: "Announcements", icon: "bell" },
    { href: "/profile", label: "Profile", icon: "user" },
  ],
  instructor: [
    { href: "/dashboard", label: "Dashboard", icon: "home" },
    { href: "/training", label: "Training", icon: "book" },
    { href: "/sessions", label: "Sessions", icon: "calendar" },
    { href: "/attendance", label: "Attendance", icon: "scan" },
    { href: "/students", label: "Students", icon: "users" },
    { href: "/announcements", label: "Announcements", icon: "bell" },
    { href: "/profile", label: "Profile", icon: "user" },
  ],
  supervisor: [
    { href: "/dashboard", label: "Dashboard", icon: "home" },
    { href: "/projects", label: "Projects", icon: "folder" },
    { href: "/submissions", label: "Submissions", icon: "file" },
    { href: "/students", label: "Students", icon: "users" },
    { href: "/profile", label: "Profile", icon: "user" },
  ],
  admin: [
    { href: "/dashboard", label: "Dashboard", icon: "home" },
    { href: "/students", label: "Interns", icon: "users" },
    { href: "/training", label: "Training", icon: "book" },
    { href: "/attendance", label: "Attendance", icon: "scan" },
    { href: "/projects", label: "Projects", icon: "folder" },
    { href: "/reports", label: "Reports", icon: "chart" },
    { href: "/announcements", label: "Announcements", icon: "bell" },
    { href: "/settings", label: "Settings", icon: "settings" },
  ],
};

// Detail routes that hang off a nav section
export const EXTRA_ROUTES: Record<Role, string[]> = {
  student: ["/projects/"],
  instructor: ["/sessions/"],
  supervisor: ["/projects/"],
  admin: ["/sessions/", "/projects/", "/profile"],
};

export const canAccess = (role: Role, path: string) =>
  NAV[role].some((n) => path === n.href || path.startsWith(n.href + "/")) || EXTRA_ROUTES[role].some((p) => path.startsWith(p));
