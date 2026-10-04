"use client";
import {
  GoogleAuthProvider, User, createUserWithEmailAndPassword, onAuthStateChanged, sendEmailVerification,
  signInWithEmailAndPassword, signInWithPopup, signOut as fbSignOut, updateProfile,
} from "firebase/auth";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { auth } from "@/lib/firebase";
import type { Profile } from "@/lib/types";

interface Ctx {
  fbUser: User | null;
  profile: Profile | null;
  loading: boolean;
  syncError: { status: number; message: string } | null;
  signIn(email: string, password: string): Promise<void>;
  signUp(name: string, email: string, password: string): Promise<void>;
  signInGoogle(): Promise<void>;
  signOut(): Promise<void>;
  resendVerification(): Promise<void>;
  recheck(): Promise<void>;
  refreshProfile(): Promise<void>;
}
const AuthCtx = createContext<Ctx>(null as unknown as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [fbUser, setFbUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncError, setSyncError] = useState<Ctx["syncError"]>(null);
  const pendingName = useRef<string | undefined>(undefined);

  const sync = useCallback(async (u: User) => {
    setSyncError(null);
    try {
      const p = await api<Profile>("/api/auth/sync", { method: "POST", body: { full_name: pendingName.current ?? u.displayName ?? undefined } });
      setProfile(p);
    } catch (e) {
      setProfile(null);
      setSyncError(e instanceof ApiError ? { status: e.status, message: e.message } : { status: 0, message: "Something went wrong" });
    }
  }, []);

  useEffect(() => {
    return onAuthStateChanged(auth, async (u) => {
      setFbUser(u);
      if (u) {
        setLoading(true);
        await sync(u);
      } else {
        setProfile(null);
        setSyncError(null);
      }
      setLoading(false);
    });
  }, [sync]);

  const value: Ctx = {
    fbUser, profile, loading, syncError,
    async signIn(email, password) { await signInWithEmailAndPassword(auth, email, password); },
    async signUp(name, email, password) {
      pendingName.current = name;
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(cred.user, { displayName: name });
      await sendEmailVerification(cred.user).catch(() => {});
    },
    async signInGoogle() { await signInWithPopup(auth, new GoogleAuthProvider()); },
    async signOut() { await fbSignOut(auth); },
    async resendVerification() { if (auth.currentUser) await sendEmailVerification(auth.currentUser); },
    async recheck() {
      const u = auth.currentUser;
      if (!u) return;
      setLoading(true);
      await u.reload();
      await u.getIdToken(true); // pick up email_verified claim
      await sync(u);
      setLoading(false);
    },
    async refreshProfile() { if (auth.currentUser) await sync(auth.currentUser); },
  };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
