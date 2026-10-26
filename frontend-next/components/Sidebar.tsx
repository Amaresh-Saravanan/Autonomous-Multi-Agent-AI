"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Map,
  Bell,
  TriangleAlert,
  ClipboardCheck,
  Package,
  Route as RouteIcon,
  HeartPulse,
  Users,
  Radio,
  Bot,
  FileText,
  KeyRound,
  SlidersHorizontal,
  ChevronsLeft,
  ChevronsRight,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useOperationsData } from "@/lib/operations-context";
import type { CurrentUser } from "@/lib/types";

const ROLE_RANK: Record<CurrentUser["role"], number> = { viewer: 0, operator: 1, admin: 2 };

type NavGroup = "Operations" | "Resources" | "System";

interface NavItem {
  href: string;
  label: string;
  minRole: CurrentUser["role"];
  icon: LucideIcon;
  group: NavGroup;
}

// Route visibility per UX_DESIGN.md §3.4's role table.
// Visual language: docs/design/stitch_eoc_command_console/kinetic_command (Kinetic
// Command design system). One icon family (lucide-react, already a
// dependency) at a single 1.75 stroke so every glyph has the same weight.
const NAV_ITEMS: NavItem[] = [
  { href: "/command", label: "Command", minRole: "viewer", icon: LayoutDashboard, group: "Operations" },
  { href: "/map", label: "Map", minRole: "viewer", icon: Map, group: "Operations" },
  { href: "/alerts", label: "Alerts", minRole: "viewer", icon: Bell, group: "Operations" },
  { href: "/incidents", label: "Incidents", minRole: "viewer", icon: TriangleAlert, group: "Operations" },
  { href: "/recommendations", label: "Recommendations", minRole: "viewer", icon: ClipboardCheck, group: "Operations" },
  { href: "/resources", label: "Resources", minRole: "viewer", icon: Package, group: "Resources" },
  { href: "/routes", label: "Routes", minRole: "viewer", icon: RouteIcon, group: "Resources" },
  { href: "/medical", label: "Medical", minRole: "viewer", icon: HeartPulse, group: "Resources" },
  { href: "/citizens", label: "Citizens", minRole: "viewer", icon: Users, group: "Resources" },
  { href: "/data-sources", label: "Data Sources", minRole: "viewer", icon: Radio, group: "System" },
  { href: "/agents", label: "Agents", minRole: "operator", icon: Bot, group: "System" },
  { href: "/audit", label: "Audit", minRole: "admin", icon: FileText, group: "System" },
  { href: "/access", label: "Access", minRole: "admin", icon: KeyRound, group: "System" },
  { href: "/settings", label: "Settings", minRole: "viewer", icon: SlidersHorizontal, group: "System" },
];

const GROUPS: NavGroup[] = ["Operations", "Resources", "System"];

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
  const { recommendations } = useOperationsData();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  if (!user) return null;

  const visible = NAV_ITEMS.filter((item) => ROLE_RANK[user.role] >= ROLE_RANK[item.minRole]);
  const pendingRecs = recommendations.filter((r) => r.status === "pending").length;

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
        aria-label="Primary"
        className={`fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col border-r border-console-outline-variant/20 bg-console-surface/95 backdrop-blur-xl transition-transform duration-200 md:static md:z-auto md:translate-x-0 md:bg-console-surface/60 md:transition-[width] ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } ${collapsed ? "md:w-16" : "w-[232px]"}`}
      >
        <div className="flex items-center gap-console-md border-b border-console-outline-variant/20 p-console-md">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] border border-console-outline-variant/40 bg-console-surface-container">
            <ShieldCheck className="h-[18px] w-[18px] text-console-primary" strokeWidth={1.75} />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h2 className="truncate font-console-body-compact text-console-body-compact font-semibold text-console-on-surface">
                Command Console
              </h2>
              <p className="truncate font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                Active Ops
              </p>
            </div>
          )}
        </div>

        <div className="flex flex-1 flex-col overflow-y-auto px-console-sm py-console-sm">
          {GROUPS.map((group, gi) => {
            const items = visible.filter((item) => item.group === group);
            if (items.length === 0) return null;
            return (
              <div key={group} className="flex flex-col gap-0.5">
                {collapsed ? (
                  gi > 0 && <div className="mx-console-sm my-console-sm h-px bg-console-outline-variant/30" />
                ) : (
                  <div
                    className={`px-console-md pb-1.5 font-console-label-caps text-[10px] font-semibold uppercase tracking-[0.12em] text-console-outline ${
                      gi > 0 ? "pt-console-lg" : "pt-console-sm"
                    }`}
                  >
                    {group}
                  </div>
                )}
                {items.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(item.href + "/");
                  const Icon = item.icon;
                  const badge = item.href === "/recommendations" && pendingRecs > 0 ? pendingRecs : 0;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onClose}
                      title={collapsed ? item.label : undefined}
                      aria-current={active ? "page" : undefined}
                      className={`flex h-9 items-center gap-console-md rounded-lg px-console-md transition-colors duration-150 ${
                        active
                          ? "bg-console-primary/[0.12] text-console-on-surface shadow-[inset_2px_0_0_var(--color-console-primary)]"
                          : "text-console-on-surface-variant hover:bg-console-on-surface/[0.04] hover:text-console-on-surface"
                      }`}
                    >
                      <Icon
                        className={`h-[18px] w-[18px] shrink-0 ${active ? "text-console-primary" : ""}`}
                        strokeWidth={1.75}
                      />
                      {!collapsed && (
                        <>
                          <span className="flex-1 truncate font-console-body-compact text-console-body-compact font-medium">
                            {item.label}
                          </span>
                          {badge > 0 && (
                            <span className="rounded-full bg-console-primary/[0.16] px-1.5 font-console-data-tabular text-[11px] font-semibold text-console-primary">
                              {badge}
                            </span>
                          )}
                        </>
                      )}
                    </Link>
                  );
                })}
              </div>
            );
          })}
        </div>

        <button
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="hidden items-center justify-center gap-console-sm border-t border-console-outline-variant/20 p-console-md text-console-on-surface-variant transition-colors hover:bg-console-surface-container/40 hover:text-console-on-surface md:flex"
        >
          {collapsed ? (
            <ChevronsRight className="h-4 w-4" strokeWidth={1.75} />
          ) : (
            <ChevronsLeft className="h-4 w-4" strokeWidth={1.75} />
          )}
          {!collapsed && <span className="font-console-body-sm text-console-body-sm">Collapse</span>}
        </button>
      </nav>
    </>
  );
}
