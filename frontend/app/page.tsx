"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Spinner } from "@/components/ui";

export default function Home() {
  const { fbUser, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading) router.replace(fbUser ? "/dashboard" : "/login");
  }, [loading, fbUser, router]);
  return <div className="p-8"><Spinner /></div>;
}
