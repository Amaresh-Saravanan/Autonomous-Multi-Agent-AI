import Link from "next/link";
import type { ReactNode } from "react";
import ThemeToggle from "@/components/ThemeToggle";

// Minimal centered shell for the public account pages (signup / recovery).
export default function AuthPageShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen w-screen items-center justify-center px-6 py-12" style={{ background: "var(--bg-base)" }}>
      <div className="absolute right-4 top-4 z-20">
        <ThemeToggle />
      </div>
      <div className="glass-panel w-full max-w-md p-8">
        <div className="mb-3 text-xs font-bold tracking-[0.3em] text-(--accent) uppercase">EOC Platform</div>
        <h1 className="text-lg font-semibold text-(--text-primary)">{title}</h1>
        <p className="mt-1 text-xs text-(--text-muted)">{subtitle}</p>
        <div className="mt-5 text-sm text-(--text-primary)">{children}</div>
        <Link href="/login" className="mt-6 block text-center text-xs text-(--text-muted) hover:text-(--text-primary)">
          ← Back to sign in
        </Link>
      </div>
    </div>
  );
}
