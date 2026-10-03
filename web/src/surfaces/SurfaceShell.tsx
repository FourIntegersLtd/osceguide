"use client";

import dynamic from "next/dynamic";
import type { ReactNode } from "react";
import type { SurfaceManifest } from "@/surfaces/contract";
import { ShellFallback } from "@/surfaces/ShellFallback";
import type { Workspace } from "@/foundation/routing";

const WorkspaceShell = dynamic(
  () =>
    import("@/surfaces/WorkspaceShell").then((mod) => ({
      default: mod.WorkspaceShell,
    })),
  { loading: () => <ShellFallback /> },
);

const PlatformStaffShell = dynamic(
  () =>
    import("@/surfaces/platform/PlatformStaffShell").then((mod) => ({
      default: mod.PlatformStaffShell,
    })),
  { loading: () => <ShellFallback /> },
);

export interface SurfaceShellProps {
  manifest: SurfaceManifest;
  /** The workspace this shell is showing, or null for the staff console. */
  workspace: Workspace | null;
  /** Everything below this shell hangs off here, e.g. `/app/kings`. */
  basePath: string;
  children: ReactNode;
}

/**
 * The frame every arm shares.
 *
 * A workspace, whichever arm it belongs to, gets the one workspace shell; an
 * arm is a manifest (its label, its navigation, which workspaces reach it) and
 * `data-surface` is the whole of the visual difference between them. The staff
 * console has no workspace and keeps its own shell.
 */
export function SurfaceShell({ manifest, workspace, basePath, children }: SurfaceShellProps) {
  if (workspace) {
    return (
      <WorkspaceShell manifest={manifest} workspace={workspace} basePath={basePath}>
        {children}
      </WorkspaceShell>
    );
  }

  return (
    <PlatformStaffShell manifest={manifest} basePath={basePath}>
      {children}
    </PlatformStaffShell>
  );
}
