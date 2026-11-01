"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { classifyExam, useCurrentExam, useSession } from "@/foundation/session";
import { capabilitiesFor, capabilityById } from "@/capabilities";
import { resolveWorkspace } from "@/surfaces/resolveWorkspace";
import { surfaceForWorkspace } from "@/surfaces/registry";
import { examForFilter } from "@/surfaces/examNav";

export type CapabilityGate = "loading" | "allowed" | "bounce" | "missing";

/**
 * Whether this arm may open the capability's page, read from the registry the navigation reads.
 *
 * "loading" only for a capability that names its exams, whose answer waits on the person's
 * exam. "bounce" sends an arm that does not mount it to the capability's `unmountedGoesTo`
 * (this hook does the redirect); "missing" is a 404.
 */
export function useCapabilityGate(id: string): CapabilityGate {
  const router = useRouter();
  const { session } = useSession();
  const { code, loading: examLoading, error: examError } = useCurrentExam();
  const { workspace: slug } = useParams<{ workspace: string }>();

  const workspace = resolveWorkspace(slug ?? "", session?.user ?? null);
  const capability = capabilityById(id);
  const mounted = workspace
    ? capabilitiesFor(surfaceForWorkspace(workspace).id, {
        can: session?.capabilities.can ?? {},
        includeHidden: true,
        // Same exam filter as the menu, so a URL cannot reach what the menu hides for this exam.
        examCode: examForFilter({ code, loading: examLoading }),
      }).some((entry) => entry.id === id)
    : false;

  // A capability that names no exams is not filtered by exam, so its answer does not change when the exam arrives.
  // Only the genuinely unknown exam waits: a reload keeps the last known code, and blanking the page for it is a flash.
  const waiting = Boolean(capability?.exams) && classifyExam({ code, loading: examLoading, error: examError }).kind === "loading";
  const bounceHref = !waiting && !mounted && workspace && capability?.unmountedGoesTo ? `/app/${slug}${capability.unmountedGoesTo}` : null;

  useEffect(() => {
    if (bounceHref) router.replace(bounceHref);
  }, [bounceHref, router]);

  if (waiting) return "loading";
  if (mounted) return "allowed";
  return bounceHref ? "bounce" : "missing";
}
