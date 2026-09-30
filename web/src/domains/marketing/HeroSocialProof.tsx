"use client";

import { useEffect, useState } from "react";
import { fetchLandingStats } from "@/domains/marketing/support/landingStats";
import { LandingGlyphBadge } from "./LandingIconBadge";
import { useLandingVariant } from "./LandingVariantContext";

type HeroSocialProofProps = {
  testimonialsHref?: string;
};

export function HeroSocialProof({
  testimonialsHref = "#testimonials",
}: HeroSocialProofProps) {
  const { type } = useLandingVariant();
  const [consultations, setConsultations] = useState<number | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      const stats = await fetchLandingStats();
      const count = Number(stats?.all_consultations ?? 0);
      // A figure nobody can verify is worse than the floor below, so a missing
      // stats route leaves the copy's own number standing.
      setConsultations(count > 0 ? count : null);
    };

    fetchStats();
  }, []);

  const formattedCount =
    consultations !== null ? `${consultations.toLocaleString()}+` : "9,700+";

  return (
    <div
      className="flex flex-wrap items-center justify-center gap-x-3.5 gap-y-2 font-landing-body text-sm leading-normal text-landing-ink-body"
    >
      <span className="inline-flex items-center gap-2">
        <LandingGlyphBadge color="green">✓</LandingGlyphBadge>
        <span>
          <strong className="font-semibold text-osce-ink-900">
            {formattedCount}
          </strong>{" "}
          consultations completed
        </span>
      </span>
      <a
        href={testimonialsHref}
        className={`${type.linkAction} underline underline-offset-4`}
      >
        Read our success stories
      </a>
    </div>
  );
}
