"use client";

import { FiCheck } from "react-icons/fi";
import { HERO } from "@/domains/marketing/landingCopy";
import { useLandingStat } from "@/domains/marketing/support/useLandingStat";

/** "14,212 cases marked so far" from the site statistics, then one doctor's line. Nothing at all when the count is unavailable. */
export function HeroProofLine() {
  const count = useLandingStat("all_feedback");
  if (count === null) return null;
  return (
    <p className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-site-body">
      <span className="inline-flex items-center gap-2">
        <FiCheck aria-hidden className="text-site-brand" />
        <strong className="font-semibold text-site-ink">{count.toLocaleString("en-GB")}</strong> cases marked so far
      </span>
      <span aria-hidden className="hidden h-4 w-px bg-site-rule sm:block" />
      <span>
        &ldquo;{HERO.proofQuote}&rdquo; <b className="text-site-ink">{HERO.proofName}</b>
      </span>
    </p>
  );
}
