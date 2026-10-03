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
 * console has no workspace and gets the same shell with a fixed name.
 */
export function SurfaceShell({ manifest, workspace, basePath, children }: SurfaceShellProps) {
  return (
    <WorkspaceShell manifest={manifest} workspace={workspace ?? undefined} basePath={basePath}>
      {children}
    </WorkspaceShell>
  );
}
