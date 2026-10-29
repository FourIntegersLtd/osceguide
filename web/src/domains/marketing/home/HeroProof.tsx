"use client";

import { useEffect, useState } from "react";
import { FiCheck } from "react-icons/fi";
import { fetchLandingStats } from "@/domains/marketing/support/landingStats";

/** The consultations figure beside the link to the success stories. Live count, with the copy's own floor when the route is down. */
export function HeroProof() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchLandingStats().then((stats) => {
      const n = Number(stats?.all_consultations ?? 0);
      if (alive) setCount(n > 0 ? n : null);
    });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-sm text-site-body">
      <span className="inline-flex items-center gap-2">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-site-pale text-site-brand">
          <FiCheck aria-hidden size={13} />
        </span>
        <span>
          <strong className="font-semibold text-site-ink">{count !== null ? `${count.toLocaleString()}+` : "9,700+"}</strong> consultations
          completed
        </span>
      </span>
      <a href="#testimonials" className="font-medium text-site-brand underline underline-offset-4">
        Read our success stories
      </a>
    </div>
  );
}
