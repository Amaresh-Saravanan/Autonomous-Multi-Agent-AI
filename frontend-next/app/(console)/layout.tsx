"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { OperationsDataProvider } from "@/lib/operations-context";
import Sidebar from "@/components/Sidebar";
import ConsoleTopbar from "@/components/ConsoleTopbar";
import LoginOverlay from "@/components/LoginOverlay";

// Shared shell for every authenticated route (plan Phase M, UX_DESIGN §3.2).
// /login doesn't exist yet (plan Phase N) so the auth gate stays inline here
// for now, same behavior as the old single-page dashboard's guard.
export default function ConsoleLayout({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  if (!user) return <LoginOverlay />;

  return (
    <OperationsDataProvider>
      <div className="flex h-screen w-screen flex-col overflow-hidden">
        <ConsoleTopbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="relative flex-1 overflow-hidden">{children}</main>
        </div>
      </div>
    </OperationsDataProvider>
  );
}
