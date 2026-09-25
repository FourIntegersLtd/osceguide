/*
 * A capability page: the same component on every arm that mounts it.
 *
 * Reached from an empty dashboard and from settings, not from navigation —
 * the capability is `hidden`, which is what keeps a one-off walkthrough out of
 * the sidebar for everybody who has already watched it.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { OnboardingScreen } from "@/capabilities/onboarding/OnboardingScreen";

export const metadata: Metadata = { title: "Meet Athena" };

export default function Page() {
  return <Capability id="onboarding"><OnboardingScreen /></Capability>;
}
