"use client";

import { boardBtn } from "@/foundation/ui/boardKit";
import Link from "next/link";
import { Fragment, useState } from "react";
import { b2bTokens, cn } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { OrgSetup } from "@/domains/assess/dashboard/api";
import { assistantPieces, assistantSteps, firstOpenStep, showsSkip, stepBlock } from "@/domains/assess/dashboard/setupSteps";
import { TEMPLATE_CSV } from "@/domains/assess/roster/csv";
import { useAssessWords } from "@/capabilities/assess-words";

/** Saves the spreadsheet template to the browser's downloads. */
function downloadTemplate() {
  const url = URL.createObjectURL(new Blob([TEMPLATE_CSV], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "people-template.csv";
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Until the first sitting is possible: five steps, one at a time, from the flags `/dashboard`
 * already returns. A button that cannot be used yet is disabled, says why and links to the fix.
 * Any step can be reopened from the list; "Skip for now" shows only on the optional step.
 * Drawn to docs/institution-overhaul/boards/Main.dc.html through the `assess*` tokens.
 */
export function SetupAssistant({ orgName, setup }: { orgName: string; setup: OrgSetup }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const steps = assistantSteps(setup, w);
  const [chosen, setChosen] = useState<number | null>(null);
  const [showPieces, setShowPieces] = useState(true);
  const index = chosen ?? firstOpenStep(steps);
  const cur = steps[index];
  const t = b2bTokens;

  if (!cur) return null;
  const blocked = stepBlock(cur, setup, w);

  return (
    <section className="flex flex-col gap-6" aria-label="Setup">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className={t.assessEyebrow}>Welcome</div>
          <h1 className={t.assessTitle}>{`Let's get ${orgName} ready for its first ${w.sitting}`}</h1>
          <p className={t.assessDesc}>Five steps. We show one at a time, and you can come back to any of them.</p>
        </div>
        <button
          type="button"
          aria-label="How the pieces fit"
          aria-expanded={showPieces}
          onClick={() => setShowPieces((open) => !open)}
          className={t.assessHelpButton}
        >
          ?
        </button>
      </div>

      <div className={cn("flex flex-wrap", t.assessCard)}>
        <div className="box-border flex-[1_1_280px] max-w-[340px] border-r border-osce-border-light p-4">
          <div className={cn(t.assessEyebrow, "px-3.5 pb-2.5 pt-1")}>{`Step ${index + 1} of 5`}</div>
          <ol className="flex flex-col gap-1">
            {steps.map((step, position) => (
              <li key={step.id}>
                <button
                  type="button"
                  aria-current={position === index ? "step" : undefined}
                  onClick={() => setChosen(position)}
                  className={position === index ? t.assessStepRowOn : t.assessStepRow}
                >
                  <span
                    aria-hidden
                    className={step.done ? t.assessDotDone : position === index ? t.assessDotCurrent : t.assessDotIdle}
                  >
                    {step.done ? "✓" : position + 1}
                  </span>
                  <span className="flex-1">{step.label}</span>
                  {step.optional ? <span className={t.assessMeta}>Optional</span> : null}
                </button>
              </li>
            ))}
          </ol>
        </div>

        <div className="flex min-w-0 flex-[999_1_472px] flex-col gap-4 px-9 py-8">
          <span className={cn(t.assessChipInfo, "self-start")}>{cur.tag}</span>
          <h2 className="text-assess-h2 font-semibold text-osce-ink-900">{cur.title}</h2>
          <p className={t.assessDesc}>{cur.body}</p>
          <div className={t.assessWhyPanel}>
            <div className={cn(t.assessMeta, "font-medium text-osce-ink-700")}>{cur.whyTitle}</div>
            <div className={t.assessMeta}>{cur.why}</div>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {blocked ? (
              <>
                <button type="button" disabled aria-describedby="step-blocked" className={boardBtn("primary")}>
                  {cur.cta}
                </button>
                <p id="step-blocked" className={t.assessMeta}>
                  {`${blocked.reason} `}
                  <Link href={hrefFor(blocked.fixHref)} className={t.b2bLink}>
                    {blocked.fixLabel}
                  </Link>
                </p>
              </>
            ) : (
              <Link href={hrefFor(cur.href)} className={boardBtn("primary")}>
                {cur.cta}
              </Link>
            )}
            {cur.alt && cur.altDownload ? (
              <button type="button" onClick={downloadTemplate} className={boardBtn()}>
                {cur.alt}
              </button>
            ) : null}
            {cur.alt && cur.altHref ? (
              <Link href={hrefFor(cur.altHref)} className={boardBtn()}>
                {cur.alt}
              </Link>
            ) : null}
            {showsSkip(steps, index) ? (
              <button type="button" onClick={() => setChosen(index + 1)} className={boardBtn()}>
                Skip for now
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {showPieces ? (
        <div>
          <div className={cn(t.assessEyebrow, "mb-2.5")}>How the pieces fit</div>
          <div className={cn("flex flex-wrap items-center gap-3 px-6 py-5", t.assessCard)}>
            {assistantPieces(w).map((piece, position) => (
              <Fragment key={piece.title}>
                {position > 0 ? (
                  <div aria-hidden className={t.assessMeta}>
                    ›
                  </div>
                ) : null}
                <Link href={hrefFor(piece.path)} className="flex-[1_1_150px]">
                  <div className="text-assess-label font-semibold text-osce-ink-900">{piece.title}</div>
                  <div className={t.assessMeta}>{piece.body}</div>
                </Link>
              </Fragment>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
