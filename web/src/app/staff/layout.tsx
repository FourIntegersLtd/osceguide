"use client";

import dynamic from "next/dynamic";
import type { ReactNode } from "react";
import { RequireCapability, RequireSession } from "@/foundation/session";
import { surfaceManifest } from "@/surfaces";
import { ShellFallback } from "@/surfaces/ShellFallback";

const WorkspaceShell = dynamic(
  () =>
    import("@/surfaces/WorkspaceShell").then((mod) => ({
      default: mod.WorkspaceShell,
    })),
  { loading: () => <ShellFallback /> },
);

const staffManifest = surfaceManifest("platform");

/**
 * The OSCE Guide staff console.
 *
 * The one workspace shell, without a workspace: the sidebar names the console
 * and the footer links back to the staff member's own practice.
 */
export default function StaffLayout({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <WorkspaceShell manifest={staffManifest} basePath="/staff">
        <RequireCapability permission="administer_platform">{children}</RequireCapability>
      </WorkspaceShell>
    </RequireSession>
  );
}
