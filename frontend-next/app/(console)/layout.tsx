"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { OperationsDataProvider } from "@/lib/operations-context";
import Sidebar from "@/components/Sidebar";
import ConsoleTopbar from "@/components/ConsoleTopbar";

// Shared shell for every authenticated route (plan Phase M, UX_DESIGN §3.2).
// Visual language: stitch_eoc_command_console/kinetic_command (Kinetic
// Command design system) -- glassmorphic dark console shell. Deliberately
// scoped to the (console) route group, NOT app/layout.tsx (the root layout):
// wrapping the root would apply this chrome to the public landing page and
// /login too, which are meant to stay chrome-free.
// tracker 3.11.2: unauthenticated visitors are redirected to the dedicated
// /login page instead of an inline overlay, so console routes stay reachable
// only via a real URL a user can bookmark/share/return to post-login.
export default function ConsoleLayout({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const router = useRouter();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!user) router.replace("/login");
  }, [user, router]);

  if (!user) return null;

  return (
    <OperationsDataProvider>
      <div className="flex h-screen w-screen flex-col overflow-hidden bg-console-surface-container-lowest">
        <ConsoleTopbar onMenuClick={() => setMobileNavOpen((v) => !v)} />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar mobileOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
          <main className="relative flex-1 overflow-hidden">{children}</main>
        </div>
      </div>
    </OperationsDataProvider>
  );
}
