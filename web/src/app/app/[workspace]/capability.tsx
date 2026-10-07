"use client";

import { useEffect, type ReactNode } from "react";
import { notFound, useParams, useRouter } from "next/navigation";
import { useCurrentExam, useSession } from "@/foundation/session";
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
export function Capability({
  id,
  children,
  redirectTo,
}: {
  id: string;
  children: ReactNode;
  /** Where an arm that does not mount this goes, instead of a 404 (a path inside the workspace). */
  redirectTo?: string;
}) {
  const router = useRouter();
  const { session } = useSession();
  const { code: examCode, loading: examLoading } = useCurrentExam();
  const { workspace: slug } = useParams<{ workspace: string }>();

  const workspace = resolveWorkspace(slug ?? "", session?.user ?? null);
  if (!workspace) notFound();

  const mounted = capabilitiesFor(surfaceForWorkspace(workspace).id, {
    can: session?.capabilities.can ?? {},
    includeHidden: true,
    // Same exam filter as the menu, so a URL cannot reach what the menu hides for this exam.
    examCode,
  });
  const allowed = mounted.some((capability) => capability.id === id);
  const bounce = !allowed && redirectTo ? `/app/${slug}${redirectTo}` : null;

  useEffect(() => {
    if (bounce && !examLoading) router.replace(bounce);
  }, [bounce, examLoading, router]);

  // The exam is unknown until the dashboard answers; deciding sooner would 404 a page the person may open.
  if (examLoading || bounce) return null;
  if (!allowed) notFound();

  return <>{children}</>;
}
