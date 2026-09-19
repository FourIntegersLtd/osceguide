"use client";

import type { ReactNode } from "react";
import { LuCalendarDays, LuGauge, LuUsers, LuUserCog } from "react-icons/lu";
import { useSession, can } from "@/foundation/session";
import { SurfaceShell, type NavItem } from "@/surfaces/SurfaceShell";

/**
 * The institution workspace.
 *
 * Navigation is filtered by what the backend says this person may do, not by a
 * role string read here — a supervisor and an admin see different items because
 * `/me/capabilities` says so.
 */
export function AssessShell({ orgSlug, children }: { orgSlug: string; children: ReactNode }) {
  const { session } = useSession();

  const nav: NavItem[] = [
    { key: "dashboard", label: "Overview", href: `/assess/${orgSlug}`, icon: LuGauge },
    { key: "sittings", label: "Sittings", href: `/assess/${orgSlug}/sittings`, icon: LuCalendarDays },
  ];

  if (can(session, "org.trainees.read")) {
    nav.push({ key: "trainees", label: "Trainees", href: `/assess/${orgSlug}/trainees`, icon: LuUsers });
  }
  if (can(session, "org.team.manage")) {
    nav.push({ key: "team", label: "Team", href: `/assess/${orgSlug}/team`, icon: LuUserCog });
  }

  return (
    <SurfaceShell surface="assess" orgSlug={orgSlug} nav={nav} title="Institution">
      {children}
    </SurfaceShell>
  );
}
