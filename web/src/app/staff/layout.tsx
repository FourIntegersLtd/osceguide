"use client";

import type { ReactNode } from "react";
import { RequireCapability } from "@/foundation/session";
import { SurfaceShell, surfaceManifest } from "@/surfaces";

/**
 * The OSCE Guide staff console.
 *
 * Outside the workspace grammar on purpose: nobody belongs to the platform the
 * way they belong to an organisation, so there is no slug to address it by and
 * no switcher entry for it. It is reached by a permission the backend grants,
 * which is what `RequireCapability` checks.
 */
export default function StaffLayout({ children }: { children: ReactNode }) {
  return (
    <SurfaceShell manifest={surfaceManifest("platform")} workspace={null} basePath="/staff">
      <RequireCapability permission="administer_platform">{children}</RequireCapability>
    </SurfaceShell>
  );
}
