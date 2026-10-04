"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { canAccess } from "@/lib/nav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { fbUser, profile, loading, syncError, signOut, resendVerification, recheck } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    if (!loading && !fbUser) router.replace("/login");
  }, [loading, fbUser, router]);
  useEffect(() => {
    if (profile && !canAccess(profile.role, path)) router.replace("/dashboard");
  }, [profile, path, router]);

  if (loading || !fbUser) return <div className="p-8"><Spinner label="Signing you in" /></div>;

  if (syncError) {
    const needsVerify = syncError.status === 403 && /verify/i.test(syncError.message);
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
        <h1 className="text-xl font-bold">{needsVerify ? "Verify your email" : "We could not open your account"}</h1>
        <p className="text-sm text-ink-soft">{syncError.message}</p>
        {needsVerify && <p className="text-sm text-ink-soft">We sent a verification link to <b>{fbUser.email}</b>. Open it, then come back and continue.</p>}
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" onClick={recheck}>{needsVerify ? "I have verified my email" : "Try again"}</button>
          {needsVerify && <button className="btn-secondary" onClick={() => resendVerification()}>Resend email</button>}
          <button className="btn-secondary" onClick={signOut}>Sign out</button>
        </div>
      </div>
    );
  }
  if (!profile) return <div className="p-8"><Spinner /></div>;
  return <AppShell>{children}</AppShell>;
}
