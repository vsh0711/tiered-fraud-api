"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, GitCompare, History, LogOut, Radar, Workflow } from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Overview", icon: Activity },
  { href: "/dashboard/playground", label: "Playground", icon: GitCompare },
  { href: "/dashboard/history", label: "History", icon: History },
  { href: "/dashboard/drift", label: "Drift", icon: Radar },
  { href: "/dashboard/jobs", label: "Jobs", icon: Workflow },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen grid-fade">
      <div className="mx-auto flex min-h-screen max-w-7xl gap-6 px-4 py-5 md:px-6">
        <aside className="panel sticky top-5 hidden h-[calc(100vh-2.5rem)] w-60 shrink-0 flex-col rounded-2xl p-4 md:flex">
          <div className="mb-8">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--accent)]">Tiered Fraud</p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight">Ops Console</h1>
            <p className="mt-2 text-sm text-[var(--muted)]">OR router · cascade · latency budget</p>
          </div>
          <nav className="flex flex-1 flex-col gap-1">
            {nav.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition ${
                    active
                      ? "bg-teal-400/15 text-teal-200"
                      : "text-[var(--muted)] hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <Icon size={16} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <button
            className="mt-4 flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-[var(--muted)] hover:bg-white/5 hover:text-white"
            onClick={() => {
              localStorage.removeItem("fraud_token");
              router.push("/");
            }}
          >
            <LogOut size={16} />
            Sign out
          </button>
        </aside>
        <main className="min-w-0 flex-1 animate-rise">{children}</main>
      </div>
    </div>
  );
}
