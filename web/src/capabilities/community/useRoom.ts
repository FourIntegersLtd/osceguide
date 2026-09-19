"use client";

import { useMemo } from "react";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { PUBLIC_ROOM, type Room } from "@/capabilities/community/api";

/**
 * Which room this screen is talking in.
 *
 * The backend addresses a post to everybody, to one organisation or to one
 * group, and that is the whole of what makes these screens mountable by an
 * institution: the same list, the same composer, a different audience. The
 * capability learns the workspace from `useSurface()` — a slug — and turns it
 * into the organisation's id with the memberships the session already carries,
 * because the audience filter is keyed on the id.
 *
 * A personal workspace has no organisation, so it passes no audience at all:
 * the backend then answers with the public pool *and* every room the person is
 * in, which is what a single feed should be.
 */
export function useRoom(explicitOrgId?: string | null): Room {
  const { orgSlug } = useSurface();
  const { session } = useSession();
  const memberships = session?.user.memberships;

  return useMemo(() => {
    if (explicitOrgId) return { visibility: "organisation", orgId: explicitOrgId };
    if (!orgSlug) return PUBLIC_ROOM;
    const membership = (memberships ?? []).find((m) => m.org_slug === orgSlug);
    // Not a member of the workspace we are standing in: ask for nothing rather
    // than silently widening to the public board.
    if (!membership) return PUBLIC_ROOM;
    return { visibility: "organisation", orgId: membership.org_id };
  }, [explicitOrgId, orgSlug, memberships]);
}

/** The organisation's own name, for the copy that says whose room this is. */
export function useRoomName(): string | null {
  const { orgSlug } = useSurface();
  const { session } = useSession();
  if (!orgSlug) return null;
  const membership = (session?.user.memberships ?? []).find((m) => m.org_slug === orgSlug);
  return membership?.org_name ?? membership?.org_slug ?? null;
}
