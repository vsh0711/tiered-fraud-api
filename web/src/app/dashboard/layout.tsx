"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("fraud_token");
    if (!token) {
      router.replace("/");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) {
    return <div className="grid-fade flex min-h-screen items-center justify-center text-[var(--muted)]">Loading…</div>;
  }
  return <Shell>{children}</Shell>;
}
