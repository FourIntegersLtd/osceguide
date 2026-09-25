import { platformRequest, type components } from "@/foundation/platform-client";

export type OnboardingScenes = components["schemas"]["OnboardingScenes"];
export type OnboardingScene = components["schemas"]["OnboardingScene"];

/**
 * The demo scenarios for the caller's exam, from the content pack the voice
 * session is rendered from.
 *
 * The exam is the backend's to decide — it reads it off the caller — so
 * nothing here passes one. That is the difference from the retiring client,
 * which sent `app_type` and could therefore ask for one exam's scenes while
 * the voice session spoke another's.
 */
export function fetchOnboardingScenes(signal?: AbortSignal): Promise<OnboardingScenes> {
  return platformRequest<OnboardingScenes>("/api/v1/assistant/onboarding-scenes", { signal });
}
