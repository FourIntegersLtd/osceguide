"use client";

import type { ReactNode } from "react";
import { LuBuilding2, LuGauge, LuUsers } from "react-icons/lu";
import { SurfaceShell, type NavItem } from "@/surfaces/SurfaceShell";

/**
 * The OSCE Guide staff console.
 *
 * Not an arm: nobody buys this. It is deliberately the plainest skin so it is
 * never mistaken for a customer's screen in a screenshot.
 */
const NAV: NavItem[] = [
  { key: "overview", label: "Overview", href: "/platform", icon: LuGauge },
  { key: "orgs", label: "Organisations", href: "/platform/organizations", icon: LuBuilding2 },
  { key: "users", label: "Users", href: "/platform/users", icon: LuUsers },
];

export function PlatformShell({ children }: { children: ReactNode }) {
  return (
    <SurfaceShell surface="platform" nav={NAV} title="OSCE Guide staff">
      {children}
    </SurfaceShell>
  );
}
