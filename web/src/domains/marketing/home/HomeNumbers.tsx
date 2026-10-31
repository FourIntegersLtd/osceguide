"use client";

import { useEffect, useState } from "react";
import { fetchLandingStats, type LandingStats } from "@/domains/marketing/support/landingStats";
import { SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

const CARDS: ReadonlyArray<{ label: string; value: (s: LandingStats) => string | number }> = [
  { label: "Consultations completed", value: (s) => s.all_consultations ?? 0 },
  { label: "Minutes of practice", value: () => "120,000+" },
  { label: "Debriefs completed", value: (s) => s.all_debriefs ?? 0 },
  { label: "AI feedback reports generated", value: (s) => s.all_feedback ?? 0 },
];

/** The community figures. Hidden until the live counts load, and for good if they cannot: no number is invented. */
export function HomeNumbers() {
  const [stats, setStats] = useState<LandingStats | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchLandingStats().then((s) => {
      if (alive) setStats(s);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!stats) return null;

  return (
    <Section tone="navy">
      <SectionHead
        onNavy
        title="Join our growing community"
        sub="Master your clinical simulation exams with AI-powered practice and personalised feedback"
      />
      <div className="mt-12 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map((c) => {
          const v = c.value(stats);
          return (
            <div key={c.label} className="rounded-2xl border border-white/15 bg-white/5 p-4 text-center sm:p-6">
              <div className="font-landing-heading text-2xl font-bold text-white sm:text-3xl">{typeof v === "number" ? v.toLocaleString() : v}</div>
              <div className="mt-2 text-sm text-site-on-navy">{c.label}</div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
