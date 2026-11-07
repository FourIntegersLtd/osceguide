"use client";

import Link from "next/link";
import { boardBtn, boardCard } from "@/foundation/ui/boardKit";
import { b2bTokens as t } from "@/foundation/ui";
import { StepRail } from "@/foundation/ui/StepRail";
import { useSurface } from "@/capabilities";
import type { OrgSetup } from "@/domains/assess/dashboard/api";
import { hireSetupSteps, nextHireStep } from "@/domains/assess/dashboard/hireSteps";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/** The employer's first-assessment checklist: the rail, then the one next step. Drawn from HireHome's New account state. */
export function HireSetup({ orgName, setup }: { orgName: string; setup: OrgSetup }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const steps = hireSetupSteps(setup, w);
  const next = nextHireStep(steps);
  return (
    <section aria-label="First assessment" className="flex flex-col gap-6">
      <div>
        <div className={t.assessEyebrow}>{orgName}</div>
        <h1 className={t.assessTitle}>{`Welcome. Four steps to your first ${w.sitting}`}</h1>
        <p className={t.assessDesc}>Do them in order. Each one takes a few minutes.</p>
      </div>
      <StepRail board steps={steps} current={next?.id} />
      {next ? (
        <div className={`${boardCard} flex flex-wrap items-center justify-between gap-4 p-6`}>
          <div className="min-w-0 flex-[1_1_300px]">
            <div className={t.assessEyebrow}>Next step</div>
            <h2 className="mt-1 text-assess-h2 font-semibold text-osce-ink-900">{next.title}</h2>
            <p className={t.assessMeta}>{next.body}</p>
          </div>
          <Link href={hrefFor(next.href)} className={boardBtn("primary")}>
            {next.cta}
          </Link>
        </div>
      ) : null}
    </section>
  );
}
