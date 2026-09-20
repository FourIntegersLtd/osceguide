"use client";

import dynamic from "next/dynamic";
import type { ReactNode } from "react";
import { RequireCapability, RequireSession } from "@/foundation/session";
import { surfaceManifest } from "@/surfaces";
import { ShellFallback } from "@/surfaces/ShellFallback";

const PlatformStaffShell = dynamic(
  () =>
    import("@/surfaces/platform/PlatformStaffShell").then((mod) => ({
      default: mod.PlatformStaffShell,
    })),
  { loading: () => <ShellFallback /> },
);

const staffManifest = surfaceManifest("platform");

/**
 * The OSCE Guide staff console.
 *
 * Uses `PlatformStaffShell` directly (not `SurfaceShell`) so staff routes do not
 * pull the institution/consumer shell code into the dev bundle.
 */
export default function StaffLayout({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <PlatformStaffShell manifest={staffManifest} basePath="/staff">
        <RequireCapability permission="administer_platform">{children}</RequireCapability>
      </PlatformStaffShell>
    </RequireSession>
  );
}
