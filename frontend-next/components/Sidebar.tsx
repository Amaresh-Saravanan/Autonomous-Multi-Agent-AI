"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Map,
  AlertTriangle,
  Siren,
  ThumbsUp,
  Package,
  Route as RouteIcon,
  Stethoscope,
  Users,
  Bot,
  History,
  Settings,
  ChevronsLeft,
  ChevronsRight,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import type { CurrentUser } from "@/lib/types";

const ROLE_RANK: Record<CurrentUser["role"], number> = { viewer: 0, operator: 1, admin: 2 };

interface NavItem {
  href: string;
  label: string;
  minRole: CurrentUser["role"];
  icon: LucideIcon;
}

// Route visibility per UX_DESIGN.md §3.4's role table. Most of these pages
// don't exist yet (tracker 3.11.6, plan Phase Q) -- this is the nav skeleton
// the shell (Phase M) ships with; links 404 until their page lands.
// Visual language: stitch_eoc_command_console/kinetic_command (Kinetic
// Command design system). Icons use lucide-react (already a dependency)
// as stand-ins for the mockup's Material Symbols glyphs, avoiding a second
// icon font/webfont request.
const NAV_ITEMS: NavItem[] = [
  { href: "/command", label: "Command", minRole: "viewer", icon: LayoutDashboard },
  { href: "/map", label: "Map", minRole: "viewer", icon: Map },
  { href: "/alerts", label: "Alerts", minRole: "viewer", icon: AlertTriangle },
  { href: "/incidents", label: "Incidents", minRole: "viewer", icon: Siren },
  { href: "/recommendations", label: "Recommendations", minRole: "viewer", icon: ThumbsUp },
  { href: "/resources", label: "Resources", minRole: "viewer", icon: Package },
  { href: "/routes", label: "Routes", minRole: "viewer", icon: RouteIcon },
  { href: "/medical", label: "Medical", minRole: "viewer", icon: Stethoscope },
  { href: "/citizens", label: "Citizens", minRole: "viewer", icon: Users },
  { href: "/agents", label: "Agents", minRole: "operator", icon: Bot },
  { href: "/audit", label: "Audit", minRole: "admin", icon: History },
  { href: "/settings", label: "Settings", minRole: "viewer", icon: Settings },
];

// mobileOpen/onClose (tracker 3.11.8): below the md breakpoint the sidebar
// becomes a fixed overlay drawer instead of taking up permanent flex-row
// space, toggled from ConsoleTopbar's hamburger button. Desktop behavior
// (collapse toggle, static flex-row placement) is unchanged at md:+.
export default function Sidebar({
  mobileOpen = false,
  onClose,
}: {
  mobileOpen?: boolean;
  onClose?: () => void;
}) {
  const { user } = useAuth();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  if (!user) return null;

  const visible = NAV_ITEMS.filter((item) => ROLE_RANK[user.role] >= ROLE_RANK[item.minRole]);

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <nav
        className={`fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col border-r border-console-outline-variant/20 bg-console-surface/95 backdrop-blur-xl transition-transform duration-200 md:static md:z-auto md:translate-x-0 md:bg-console-surface/60 md:transition-[width] ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } ${collapsed ? "md:w-14" : "w-44"}`}
      >
      <div className="flex items-center gap-sm border-b border-console-outline-variant/20 p-md">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-console-outline/20 bg-console-surface-container-high">
          <ShieldCheck className="h-[18px] w-[18px] text-console-primary" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <h2 className="truncate font-console-label-caps text-console-label-caps text-console-on-surface">
              Command Console
            </h2>
            <p className="truncate font-console-body-sm text-console-body-sm text-console-on-surface-variant">
              Active Ops
            </p>
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-unit overflow-y-auto px-xs py-sm">
        {visible.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              title={collapsed ? item.label : undefined}
              className={`flex items-center gap-sm rounded-md px-sm py-[6px] transition-all duration-200 ease-in-out ${
                active
                  ? "border-l-2 border-console-primary bg-console-primary/10 text-console-primary"
                  : "text-console-on-surface-variant hover:bg-console-surface-container/40 hover:text-console-on-surface"
              }`}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!collapsed && (
                <span className="truncate font-console-label-caps text-console-label-caps">
                  {item.label}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      <button
        onClick={() => setCollapsed((v) => !v)}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="hidden items-center justify-center gap-sm border-t border-console-outline-variant/20 p-sm text-console-on-surface-variant hover:bg-console-surface-container/40 hover:text-console-on-surface md:flex"
      >
        {collapsed ? (
          <ChevronsRight className="h-[16px] w-[16px]" />
        ) : (
          <ChevronsLeft className="h-[16px] w-[16px]" />
        )}
        {!collapsed && <span className="font-console-label-caps text-console-label-caps">Collapse</span>}
      </button>
      </nav>
    </>
  );
}
