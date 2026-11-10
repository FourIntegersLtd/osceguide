"use client";

import { FiCheck } from "react-icons/fi";
import { useLandingStat } from "@/domains/marketing/support/useLandingStat";

/**
 * The consultations figure beside the link to the success stories. Live count, with the copy's own floor when the route is down.
 * `onDeep` is for the landing hero's deep-blue band: white text and a bare check.
 */
export function HeroProof({ testimonialsHref = "#testimonials", align = "center", onDeep = false }: { testimonialsHref?: string; align?: "center" | "start"; onDeep?: boolean }) {
  const count = useLandingStat("all_consultations");

  return (
    <div className={`flex flex-wrap items-center ${align === "center" ? "justify-center" : "justify-start"} gap-x-4 gap-y-2 text-sm ${onDeep ? "text-white/80 sm:text-[15px]" : "text-site-body"}`}>
      <span className="inline-flex items-center gap-2">
        {onDeep ? (
          <FiCheck aria-hidden size={18} className="text-white" />
        ) : (
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-site-pale text-site-brand">
            <FiCheck aria-hidden size={13} />
          </span>
        )}
        <span>
          <strong className={`font-semibold ${onDeep ? "text-white" : "text-site-ink"}`}>{count !== null ? `${count.toLocaleString()}+` : "9,700+"}</strong> consultations
          completed
        </span>
      </span>
      <a href={testimonialsHref} className={`font-medium underline underline-offset-4 ${onDeep ? "text-white" : "text-site-brand"}`}>
        Read our success stories
      </a>
    </div>
  );
}
