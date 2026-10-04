"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { firebaseConfigured } from "@/lib/firebase";

function friendly(code: string, fallback: string) {
  const map: Record<string, string> = {
    "auth/invalid-credential": "Email or password is incorrect.",
    "auth/wrong-password": "Email or password is incorrect.",
    "auth/user-not-found": "No account found with that email.",
    "auth/email-already-in-use": "An account with this email already exists. Sign in instead.",
    "auth/weak-password": "Use a password with at least 6 characters.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/popup-closed-by-user": "Google sign-in was cancelled.",
    "auth/too-many-requests": "Too many attempts. Wait a moment and try again.",
    "auth/network-request-failed": "Network error. Check your connection.",
  };
  return map[code] ?? fallback;
}

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const { signIn, signUp, signInGoogle, fbUser, loading } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (!loading && fbUser) router.replace("/dashboard"); }, [loading, fbUser, router]);

  async function run(fn: () => Promise<void>) {
    setBusy(true); setError(null);
    try { await fn(); } catch (e: any) { setError(friendly(e?.code ?? "", e?.message ?? "Something went wrong")); } finally { setBusy(false); }
  }

  return (
    <div className="grid min-h-screen md:grid-cols-[1fr_1.1fr]">
      <aside className="hidden flex-col justify-between bg-brand p-10 text-white md:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-white text-lg font-bold text-brand">M</div>
          <span className="font-semibold">Lagos State Ministry of Innovation, Science &amp; Technology</span>
        </div>
        <div>
          <h1 className="text-4xl font-bold leading-tight">SIWES Training &amp; Project Hub</h1>
          <p className="mt-4 max-w-md text-white/80">Training sessions, attendance and supervised projects for every SIWES intern, in one place.</p>
        </div>
        <p className="text-sm text-white/60">Student Industrial Work Experience Scheme</p>
      </aside>
      <main className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex items-center gap-2 md:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand font-bold text-white">M</div>
            <span className="text-lg font-bold">MIST SIWES Hub</span>
          </div>
          <h2 className="text-2xl font-bold">{mode === "login" ? "Sign in" : "Create your account"}</h2>
          <p className="mt-1 text-sm text-ink-soft">{mode === "login" ? "Use the email registered for your SIWES placement." : "Use the email the ministry has on record for you."}</p>
          {!firebaseConfigured && <p className="mt-4 rounded-md bg-warn-soft p-3 text-sm text-warn">Firebase is not configured. Add the NEXT_PUBLIC_FIREBASE_* values to <code>.env.local</code>.</p>}
          <form className="mt-6 space-y-4" onSubmit={(e) => { e.preventDefault(); run(() => (mode === "login" ? signIn(email, password) : signUp(name, email, password))); }}>
            {mode === "signup" && (
              <div><label className="label" htmlFor="name">Full name</label><input id="name" className="input" required minLength={2} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} /></div>
            )}
            <div><label className="label" htmlFor="email">Email</label><input id="email" type="email" className="input" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
            <div><label className="label" htmlFor="password">Password</label><input id="password" type="password" className="input" required minLength={6} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} /></div>
            {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad" role="alert">{error}</p>}
            <button className="btn-primary w-full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
          </form>
          <div className="my-5 flex items-center gap-3 text-xs text-ink-faint"><span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" /></div>
          <button className="btn-secondary w-full" disabled={busy} onClick={() => run(signInGoogle)}>
            <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden><path fill="#4285F4" d="M23 12.3c0-.8-.1-1.5-.2-2.2H12v4.2h6.2a5.3 5.3 0 01-2.3 3.5v2.9h3.7c2.2-2 3.4-5 3.4-8.4z"/><path fill="#34A853" d="M12 24c3.1 0 5.7-1 7.6-2.8l-3.7-2.9c-1 .7-2.3 1.1-3.9 1.1-3 0-5.5-2-6.4-4.7H1.8v3A12 12 0 0012 24z"/><path fill="#FBBC05" d="M5.6 14.7a7.2 7.2 0 010-4.6v-3H1.8a12 12 0 000 10.6z"/><path fill="#EA4335" d="M12 4.8c1.7 0 3.2.6 4.4 1.7l3.3-3.3A12 12 0 001.8 7.1l3.8 3c.9-2.8 3.4-5.3 6.4-5.3z"/></svg>
            Continue with Google
          </button>
          <p className="mt-6 text-center text-sm text-ink-soft">
            {mode === "login" ? <>New intern? <Link href="/signup" className="font-semibold text-brand underline">Create an account</Link></> : <>Already registered? <Link href="/login" className="font-semibold text-brand underline">Sign in</Link></>}
          </p>
        </div>
      </main>
    </div>
  );
}
