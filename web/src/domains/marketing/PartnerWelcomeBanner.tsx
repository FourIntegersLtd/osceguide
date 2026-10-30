"use client";

import { HiOutlineSparkles } from "react-icons/hi2";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import { partnerDisplayName } from "@/domains/marketing/support/partnerDisplayName";
import { cn } from "@/foundation/ui";

interface PartnerWelcomeBannerProps {
  className?: string;
  /** Short variant for auth pages. */
  compact?: boolean;
  /** `site` is for pages on the public site's tokens. */
  tone?: "app" | "site";
}

/** Acknowledges a partner referral so the handoff doesn't feel like a stray redirect. */
export function PartnerWelcomeBanner({ className = "", compact = false, tone = "app" }: PartnerWelcomeBannerProps) {
  const { partner, isPartnerVisit } = usePartnerContext();
  if (!isPartnerVisit) return null;
  const name = partnerDisplayName(partner);

  return (
    <div
      role="status"
      className={cn(
        "flex items-center gap-2 px-3 py-2",
        tone === "site"
          ? "rounded-xl border border-site-line bg-site-pale text-sm text-site-ink"
          : "rounded-osce-lg border border-osce-accent/20 bg-osce-accent-subtle text-osce-meta text-osce-ink-900",
        className,
      )}
    >
      <HiOutlineSparkles className={cn("h-4 w-4 shrink-0", tone === "site" ? "text-site-brand" : "text-osce-accent")} aria-hidden />
      <span>
        <span className="font-semibold">Welcome from {name}.</span>{" "}
        {compact
          ? "Your access is linked to this visit."
          : "Your access is linked to this visit. Create a free account to start practising."}
      </span>
    </div>
  );
}
