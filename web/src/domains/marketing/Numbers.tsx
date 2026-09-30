"use client";

import { useEffect, useState } from "react";
import { fetchLandingStats, type LandingStats } from "@/domains/marketing/support/landingStats";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";

const statCards = [
  {
    label: "Consultations completed",
    getValue: (stats: LandingStats | null) => stats?.all_consultations ?? 0,
  },
  {
    label: "Minutes of practice",
    isCustomValue: true,
    getValue: () => "120,000+",
  },
  {
    label: "Debriefs completed",
    getValue: (stats: LandingStats | null) => stats?.all_debriefs ?? 0,
  },
  {
    label: "AI feedback reports generated",
    getValue: (stats: LandingStats | null) => stats?.all_feedback ?? 0,
  },
] as const;

function StatSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {statCards.map((card) => (
        <div
          key={card.label}
          className="rounded-landing-card border border-landing-warm bg-landing-card p-6 shadow-landing-card"
        >
          <div className="h-9 w-28 animate-pulse rounded bg-landing-hairline" />
          <div className="mt-3 h-4 w-36 animate-pulse rounded bg-landing-hairline" />
        </div>
      ))}
    </div>
  );
}

function Numbers() {
  const { type } = useLandingVariant();
  const [stats, setStats] = useState<LandingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      const data = await fetchLandingStats();
      // The band is hidden rather than shown with zeroes when there are no
      // figures: an empty statistics section reads as a broken page.
      if (data) setStats(data);
      else setFailed(true);
      setLoading(false);
    };
    fetchStats();
  }, []);

  if (failed) {
    return null;
  }

  return (
    <section
      id="numbers"
      className={`scroll-mt-20 py-16 sm:py-16 ${landingSectionSurfaces.numbers}`}
    >
      <div className={type.sectionShell}>
        <h2 className={`${type.sectionTitle} max-w-[22ch]`}>
          Join our growing community
        </h2>
        <p className={`${type.sectionSubtitle} max-w-[56ch]`}>
          Master your clinical simulation exams with AI-powered practice and
          personalized feedback
        </p>

        {loading ? (
          <div className="mt-8">
            <StatSkeleton />
          </div>
        ) : (
          <div className="mt-8 grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
            {statCards.map((card) => {
              const rawValue = card.getValue(stats);
              const displayValue =
                "isCustomValue" in card && card.isCustomValue
                  ? rawValue
                  : `${Number(rawValue).toLocaleString()}+`;

              return (
                <div
                  key={card.label}
                  className="rounded-landing-card border border-landing-warm bg-landing-card px-6 py-[22px] shadow-landing-card"
                >
                  <div className="font-landing-mono text-[clamp(1.75rem,7vw,2.125rem)] font-medium leading-none text-osce-ink-900">
                    {displayValue}
                  </div>
                  <div className="mt-2.5 font-landing-body text-sm leading-relaxed text-b2c-text-secondary">
                    {card.label}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

export default Numbers;
