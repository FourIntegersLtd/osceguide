"use client";

import type { ReactNode } from "react";
import { LuCalendarDays } from "react-icons/lu";
import { SurfaceShell, type NavItem } from "@/surfaces/SurfaceShell";

/**
 * A trainee inside an institution.
 *
 * Still the Assess surface: they are a member of the organisation, and the
 * capabilities their institution mounts — study material, discussion — appear
 * for them exactly as they do for staff, filtered by the backend.
 */
const NAV: NavItem[] = [
  { key: "sittings", label: "My sittings", href: "/assess/trainee", icon: LuCalendarDays },
];

export function TraineeShell({ children }: { children: ReactNode }) {
  return (
    <SurfaceShell surface="assess" nav={NAV} title="My training">
      {children}
    </SurfaceShell>
  );
}
