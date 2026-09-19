"use client";

import type { ReactNode } from "react";
import { LuHouse, LuLayers, LuWallet } from "react-icons/lu";
import { SurfaceShell, type NavItem } from "@/surfaces/SurfaceShell";

/** Train's own destinations. Study material, stations and discussion come from the registry. */
const NAV: NavItem[] = [
  { key: "home", label: "Home", href: "/practice", icon: LuHouse },
  { key: "mocks", label: "Mocks", href: "/mocks", icon: LuLayers },
  { key: "access", label: "Access", href: "/access", icon: LuWallet },
];

export function TrainShell({ children }: { children: ReactNode }) {
  return (
    <SurfaceShell surface="train" nav={NAV} title="OSCE Guide">
      {children}
    </SurfaceShell>
  );
}
