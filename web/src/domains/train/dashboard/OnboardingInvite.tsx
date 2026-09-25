"use client";

import { useEffect, useState } from "react";
import { LuSparkles } from "react-icons/lu";
import { ButtonLink, Button, productTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { hasSeenOnboarding, rememberOnboardingSeen } from "@/capabilities/onboarding";

const { b2cCard, b2cCardPadding } = productTokens;

/**
 * The one invitation a brand-new dashboard makes.
 *
 * Shown only to somebody who has marked nothing yet and has not been through
 * the walkthrough, which is the same trigger the retiring client used before
 * it opened onboarding as a modal over the dashboard. A card rather than a
 * modal: an introduction that interrupts is the one people close without
 * reading.
 */
export function OnboardingInvite({ attempts }: { attempts: number }) {
  const { hrefFor } = useSurface();
  const [show, setShow] = useState(false);

  // localStorage is an external store, and reading it during render would
  // disagree with the server's first paint.
  useEffect(() => {
    if (attempts > 0 || hasSeenOnboarding()) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShow(true);
  }, [attempts]);

  if (!show) return null;

  return (
    <section className={`${b2cCard} ${b2cCardPadding} flex flex-wrap items-center gap-4`}>
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-subtle text-accent">
        <LuSparkles className="h-5 w-5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <h2 className="font-semibold text-ink">Meet Athena</h2>
        <p className="text-sm text-ink-muted">
          Two minutes: she introduces herself, and marks one exchange so you can hear what her
          feedback sounds like.
        </p>
      </div>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            rememberOnboardingSeen();
            setShow(false);
          }}
        >
          Not now
        </Button>
        <ButtonLink href={hrefFor("/onboarding")} variant="primary" size="sm">
          Take the tour
        </ButtonLink>
      </div>
    </section>
  );
}
