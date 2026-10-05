"use client";

import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = typeof window !== "undefined" ? localStorage.getItem("fraud_token") : null;

  if (typeof window !== "undefined" && !token) {
    router.replace("/");
    return (
      <div className="grid-fade flex min-h-screen items-center justify-center text-[var(--muted)]">
        Redirecting…
      </div>
    );
  }

  if (typeof window === "undefined") {
    return (
      <div className="grid-fade flex min-h-screen items-center justify-center text-[var(--muted)]">
        Loading…
      </div>
    );
  }

  return <Shell>{children}</Shell>;
}
