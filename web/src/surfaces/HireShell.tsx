"use client";

import type { ReactNode } from "react";
import { LuBriefcase, LuGauge } from "react-icons/lu";
import { SurfaceShell, type NavItem } from "@/surfaces/SurfaceShell";

/**
 * The employer workspace.
 *
 * An employer is an organisation running an exam-mode sitting, so this is a
 * shell over the same slices Assess uses rather than a third product. It exists
 * as its own surface for the skin and the wording, not for a second
 * implementation.
 */
export function HireShell({ orgSlug, children }: { orgSlug: string; children: ReactNode }) {
  const nav: NavItem[] = [
    { key: "dashboard", label: "Overview", href: `/hire/${orgSlug}`, icon: LuGauge },
    { key: "assessments", label: "Assessments", href: `/hire/${orgSlug}/sittings`, icon: LuBriefcase },
  ];

  return (
    <SurfaceShell surface="hire" orgSlug={orgSlug} nav={nav} title="Hiring">
      {children}
    </SurfaceShell>
  );
}
