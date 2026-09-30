"use client";

import { useMemo } from "react";
import { useSurface } from "@/capabilities";
import { authoringScope, type AuthoringScope } from "@/capabilities/authoring/api";

/**
 * The scope this mount writes into, from the surface context and nothing else.
 *
 * `SurfaceContext` is deliberately two fields and a href helper, and two
 * fields is exactly what the scope needs: an organisation's workspace owns its
 * own material, and the staff surface writes the platform catalogue. A partner
 * is an organisation, so it needs no case of its own — which is the whole
 * claim this capability makes.
 */
export function useAuthoringScope(): AuthoringScope {
  const { surface, orgSlug } = useSurface();
  return useMemo(() => authoringScope(surface, orgSlug), [surface, orgSlug]);
}
