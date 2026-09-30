"use client";

import { useRouter } from "next/navigation";
import { useSurface } from "@/capabilities/SurfaceContext";
import { OnboardingFlow } from "@/capabilities/onboarding/OnboardingFlow";
import { rememberOnboardingSeen } from "@/capabilities/onboarding/seen";

/**
 * The walkthrough as a page of its own.
 *
 * Finishing sends the person to the mocks list, which is where a first
 * consultation starts. The path comes from the surface's base rather than
 * being written out, so the same page finishes correctly on an institution
 * workspace as on a personal one.
 */
export function OnboardingScreen() {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const done = (destination: string) => {
    rememberOnboardingSeen();
    router.push(hrefFor(destination));
  };

  return (
    <div className="p-4 sm:p-6">
      <OnboardingFlow onComplete={() => done("/mocks")} onSkip={() => done("/dashboard")} />
    </div>
  );
}
