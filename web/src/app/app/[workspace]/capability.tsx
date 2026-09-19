"use client";

import type { ReactNode } from "react";
import { notFound, useParams } from "next/navigation";
import { useSession } from "@/foundation/session";
import { capabilitiesFor } from "@/capabilities";
import { resolveWorkspace, surfaceForWorkspace } from "@/surfaces";

/**
 * A capability's page, on whichever arm is asking.
 *
 * The component inside is the same everywhere — that is what makes it a
 * capability — but not every arm mounts every one. This is the gate: a
 * capability that does not list this arm, or whose permission the backend has
 * not granted, is a 404 rather than a section that quietly appears for
 * somebody who cannot use it.
 *
 * It reads the same registry the navigation reads, so a page can never be
 * reachable by URL while absent from the menu, or the reverse.
 */
export function Capability({ id, children }: { id: string; children: ReactNode }) {
  const { session } = useSession();
  const { workspace: slug } = useParams<{ workspace: string }>();

  const workspace = resolveWorkspace(slug ?? "", session?.user ?? null);
  if (!workspace) notFound();

  const mounted = capabilitiesFor(surfaceForWorkspace(workspace).id, {
    can: session?.capabilities.can ?? {},
    includeHidden: true,
  });
  if (!mounted.some((capability) => capability.id === id)) notFound();

  return <>{children}</>;
}
