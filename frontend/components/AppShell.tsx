"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { NAV } from "@/lib/nav";
import { Icon } from "./ui";

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-brand text-sm font-bold text-white">M</div>
      <div className="leading-tight">
        <p className="text-[15px] font-bold text-ink">MIST SIWES Hub</p>
        <p className="text-[11px] text-ink-soft">Lagos State Ministry of Innovation, Science &amp; Technology</p>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { profile, signOut } = useAuth();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  if (!profile) return null;
  const items = NAV[profile.role];
  const active = (href: string) => path === href || path.startsWith(href + "/");
  const isStudent = profile.role === "student";
  const primary = items.filter((i) => i.primary);

  const navList = (onClick?: () => void) => (
    <nav aria-label="Main" className="space-y-0.5">
      {items.map((i) => (
        <Link key={i.href} href={i.href} onClick={onClick} aria-current={active(i.href) ? "page" : undefined}
          className={`flex min-h-[44px] items-center gap-3 rounded-md px-3 text-sm font-semibold ${active(i.href) ? "bg-brand text-white" : "text-ink-soft hover:bg-surface"}`}>
          <Icon name={i.icon} />{i.label}
        </Link>
      ))}
    </nav>
  );
  const userBlock = (
    <div className="border-t border-line pt-3">
      <p className="truncate text-sm font-semibold">{profile.full_name}</p>
      <p className="mb-2 text-xs capitalize text-ink-soft">{profile.role}</p>
      <button onClick={signOut} className="btn-secondary btn-sm w-full">Sign out</button>
    </div>
  );

  return (
    <div className="min-h-screen bg-white">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col justify-between border-r border-line bg-white p-4 md:flex">
        <div className="space-y-6"><Brand />{navList()}</div>
        {userBlock}
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-white px-4 py-2.5 md:hidden"
        style={{ paddingTop: "max(0.625rem, env(safe-area-inset-top))" }}>
        <div className="flex items-center gap-2"><div className="flex h-8 w-8 items-center justify-center rounded bg-brand text-sm font-bold text-white">M</div><span className="font-bold">SIWES Hub</span></div>
        <button className="rounded p-2 text-ink" aria-label="Open menu" onClick={() => setOpen(true)}><Icon name="menu" /></button>
      </header>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-ink/40" />
          <div className="absolute inset-y-0 right-0 flex w-72 max-w-[85%] flex-col justify-between bg-white p-4" onClick={(e) => e.stopPropagation()}>
            <div className="space-y-5">
              <div className="flex justify-end"><button aria-label="Close menu" onClick={() => setOpen(false)}><Icon name="x" /></button></div>
              {navList(() => setOpen(false))}
            </div>
            {userBlock}
          </div>
        </div>
      )}

      <main className={`md:pl-64 ${isStudent ? "pb-24 md:pb-0" : ""}`}>
        <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6 sm:py-8">{children}</div>
      </main>

      {isStudent && (
        <nav aria-label="Quick navigation" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-white md:hidden"
          style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
          {primary.map((i) => (
            <Link key={i.href} href={i.href} aria-current={active(i.href) ? "page" : undefined}
              className={`flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[11px] font-semibold ${active(i.href) ? "text-brand" : "text-ink-soft"}`}>
              <Icon name={i.icon} className="h-6 w-6" />{i.label}
            </Link>
          ))}
          <button onClick={() => setOpen(true)} className="flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[11px] font-semibold text-ink-soft">
            <Icon name="more" className="h-6 w-6" />More
          </button>
        </nav>
      )}
    </div>
  );
}
