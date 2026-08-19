"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import type { CurrentUser } from "@/lib/types";

const ROLE_RANK: Record<CurrentUser["role"], number> = { viewer: 0, operator: 1, admin: 2 };

interface NavItem {
  href: string;
  label: string;
  minRole: CurrentUser["role"];
}

// Route visibility per UX_DESIGN.md §3.4's role table. Most of these pages
// don't exist yet (tracker 3.11.6, plan Phase Q) -- this is the nav skeleton
// the shell (Phase M) ships with; links 404 until their page lands.
const NAV_ITEMS: NavItem[] = [
  { href: "/command", label: "Command", minRole: "viewer" },
  { href: "/map", label: "Map", minRole: "viewer" },
  { href: "/alerts", label: "Alerts", minRole: "viewer" },
  { href: "/incidents", label: "Incidents", minRole: "viewer" },
  { href: "/recommendations", label: "Recommendations", minRole: "viewer" },
  { href: "/resources", label: "Resources", minRole: "viewer" },
  { href: "/routes", label: "Routes", minRole: "viewer" },
  { href: "/medical", label: "Medical", minRole: "viewer" },
  { href: "/citizens", label: "Citizens", minRole: "viewer" },
  { href: "/agents", label: "Agents", minRole: "operator" },
  { href: "/audit", label: "Audit", minRole: "admin" },
  { href: "/settings", label: "Settings", minRole: "viewer" },
];

export default function Sidebar() {
  const { user } = useAuth();
  const pathname = usePathname();
  if (!user) return null;

  const visible = NAV_ITEMS.filter((item) => ROLE_RANK[user.role] >= ROLE_RANK[item.minRole]);

  return (
    <nav className="glass-panel flex w-44 shrink-0 flex-col gap-1 border-r border-[var(--border)] p-2 text-xs">
      {visible.map((item) => {
        const active = pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded px-2.5 py-1.5 ${
              active
                ? "bg-[var(--accent)]/20 text-[var(--text-primary)]"
                : "text-[var(--text-muted)] hover:bg-white/5 hover:text-[var(--text-primary)]"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
