"use client";

import type { ReactNode } from "react";
import { RequireCapability, RequireSession } from "@/foundation/session";
import { SurfaceShell, surfaceManifest } from "@/surfaces";

/**
 * The OSCE Guide staff console.
 *
 * Outside the workspace grammar on purpose: nobody belongs to the platform the
 * way they belong to an organisation, so there is no slug to address it by and
 * no switcher entry for it. It is reached by a permission the backend grants.
 *
 * Both gates, and in this order. `RequireSession` sends a signed-out visitor
 * to sign in and back; `RequireCapability` then tells a signed-in person who
 * is not staff that this is not theirs. Without the first, an anonymous
 * visitor got the console's frame and a refusal card inside it — which shows
 * them the shape of a screen they should not know exists, and gives them no
 * way to sign in as somebody who may see it.
 */
export default function StaffLayout({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <SurfaceShell manifest={surfaceManifest("platform")} workspace={null} basePath="/staff">
        <RequireCapability permission="administer_platform">{children}</RequireCapability>
      </SurfaceShell>
    </RequireSession>
  );
}
