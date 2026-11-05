"use client";

import Link from "next/link";
import { useState } from "react";
import { HiOutlineQuestionMarkCircle } from "react-icons/hi2";
import { Badge, Button, ButtonLink, b2bTokens, cn } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import type { OrgSetup } from "@/domains/assess/dashboard/api";
import { assistantSteps, firstOpenStep, stepBlockedReason } from "@/domains/assess/dashboard/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * Until the first sitting is possible: five steps, one at a time, from the flags `/dashboard`
 * already returns. Every step is shown to every administrator; the button of one somebody may
 * not do is disabled and says why. Any step can be reopened, and "Skip for now" moves on.
 */
export function SetupAssistant({ orgName, setup }: { orgName: string; setup: OrgSetup }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const steps = assistantSteps(setup, w);
  const [chosen, setChosen] = useState<number | null>(null);
  const [showPieces, setShowPieces] = useState(true);
  const index = chosen ?? firstOpenStep(steps);
  const cur = steps[index];
  const pieces = [
    { title: w.Exam, body: "What is examined and how it is marked", path: "/authoring" },
    { title: "Stations", body: "The cases candidates sit", path: "/authoring/stations" },
    { title: w.People, body: `${w.Trainees} and ${w.supervisors}`, path: "/trainees" },
    { title: w.Sitting, body: "One occasion, such as the March mock", path: "/sittings" },
  ];

  if (!cur) return null;
  const blocked = stepBlockedReason(cur, (permission) => can(session, permission));

  return (
    <section className="flex flex-col gap-6" aria-label="Setup">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className={b2bTokens.b2bEyebrow}>Welcome</p>
          <h1 className="text-osce-title font-semibold text-b2b-headline">{`Let's get ${orgName} ready for its first ${w.sitting}`}</h1>
          <p className="text-osce-body text-b2b-muted">Five steps. We show one at a time, and you can come back to any of them.</p>
        </div>
        <button
          type="button"
          aria-label="How the pieces fit"
          aria-expanded={showPieces}
          onClick={() => setShowPieces((open) => !open)}
          className={b2bTokens.b2bIconButtonSm}
        >
          <HiOutlineQuestionMarkCircle className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <div className="flex flex-col gap-4 rounded-osce-2xl bg-canvas p-6">
        <p className="text-osce-meta font-medium text-b2b-muted">{`Step ${index + 1} of 5`}</p>
        <ol className="flex flex-wrap gap-2">
          {steps.map((step, position) => (
            <li key={step.id}>
              <button
                type="button"
                aria-current={position === index ? "step" : undefined}
                onClick={() => setChosen(position)}
                className={cn(
                  "flex items-center gap-2 rounded-osce-md px-3 py-1.5 text-osce-meta",
                  position === index ? "bg-white font-semibold text-b2b-headline" : "text-b2b-muted",
                )}
              >
                <span aria-hidden>{step.done ? "✓" : position + 1}</span>
                {step.label}
                {step.optional ? <span className="text-b2b-muted">Optional</span> : null}
              </button>
            </li>
          ))}
        </ol>

        <div className="flex flex-col gap-3">
          <div>
            <Badge variant={cur.optional ? "neutral" : "info"}>{cur.tag}</Badge>
          </div>
          <h2 className="text-osce-title font-semibold text-b2b-headline">{cur.title}</h2>
          <p className="text-osce-body text-b2b-body">{cur.body}</p>
          <div>
            <p className="text-osce-meta font-semibold text-b2b-headline">{cur.whyTitle}</p>
            <p className="text-osce-meta text-b2b-muted">{cur.why}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {blocked ? (
              <>
                <Button themeType="b2b" variant="commit" disabled aria-describedby="step-blocked">
                  {cur.cta}
                </Button>
                <p id="step-blocked" className="text-osce-meta text-b2b-muted">
                  {blocked}
                </p>
              </>
            ) : (
              <ButtonLink href={hrefFor(cur.href)} themeType="b2b" variant="commit">
                {cur.cta}
              </ButtonLink>
            )}
            {cur.alt && cur.altHref ? (
              <ButtonLink href={hrefFor(cur.altHref)} themeType="b2b" variant="secondary">
                {cur.alt}
              </ButtonLink>
            ) : null}
            {index < steps.length - 1 ? (
              <Button themeType="b2b" variant="secondary" onClick={() => setChosen(index + 1)}>
                Skip for now
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      {showPieces ? (
        <div className="flex flex-col gap-3">
          <p className={b2bTokens.b2bEyebrow}>How the pieces fit</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {pieces.map((piece) => (
              <Link key={piece.title} href={hrefFor(piece.path)} className="rounded-osce-xl bg-canvas p-4">
                <span className="block text-osce-body font-semibold text-b2b-headline">{piece.title}</span>
                <span className="block text-osce-meta text-b2b-muted">{piece.body}</span>
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
