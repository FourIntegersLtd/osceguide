import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";
import type { AssistantSurface } from "@/capabilities/surface";

export type AssistantSession = components["schemas"]["SessionRead"];

/**
 * What the client tells the backend about where the person is standing.
 *
 * The backend selects a help pack from surface x exam x role and renders the
 * client's own navigation labels into the answers, so the assistant says "open
 * Sittings" on an institution screen and "open Mocks" on a consumer one
 * without either client shipping a script. Mirrors
 * `assistant_content/request.py`; the caps are the backend's.
 */
export interface AssistantClientContext {
  surface: AssistantSurface;
  route: string;
  navigation: { key: string; label: string; path: string }[];
}

export const MAX_ROUTE_CHARS = 200;
export const MAX_NAV_ITEMS = 40;
export const MAX_NAV_FIELD_CHARS = 120;

const clip = (value: string, limit: number) => value.trim().slice(0, limit);

export function buildClientContext(input: {
  surface: AssistantSurface;
  pathname: string | null | undefined;
  navItems?: { key: string; label: string; path: string }[];
}): AssistantClientContext {
  return {
    surface: input.surface,
    route: clip(input.pathname ?? "", MAX_ROUTE_CHARS),
    navigation: (input.navItems ?? [])
      .filter((item) => item.key.trim().length > 0)
      .slice(0, MAX_NAV_ITEMS)
      .map((item) => ({
        key: clip(item.key, MAX_NAV_FIELD_CHARS),
        label: clip(item.label, MAX_NAV_FIELD_CHARS),
        path: clip(item.path, MAX_ROUTE_CHARS),
      })),
  };
}

export type AssistantSessionType = "help" | "onboarding" | "dashboard" | "demo";

export function startAssistantSession(
  sessionType: AssistantSessionType,
  context: AssistantClientContext,
  signal?: AbortSignal,
): Promise<AssistantSession> {
  return platformRequest<AssistantSession>("/api/v1/assistant/sessions", {
    method: "POST",
    body: { session_type: sessionType, extras: { client: context } },
    signal,
  });
}

export function assistantVoiceToken(sessionId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/assistant/sessions/${encodeURIComponent(sessionId)}/voice-token`,
    { method: "POST", signal },
  );
}
