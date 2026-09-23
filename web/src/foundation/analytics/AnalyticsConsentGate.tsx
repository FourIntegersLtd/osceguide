"use client";

import { useEffect, useState } from "react";
import Script from "next/script";
import type { ReactNode } from "react";
import CookiesConsentModal from "@/foundation/ui/CookiesConsentModal";

/**
 * Google Analytics, behind the consent that was always meant to gate it.
 *
 * The retiring client asked on first visit, stored the answer under
 * `analytics-consent`, and only then loaded gtag. This port carried the modal
 * and dropped the two things that made it mean anything — nothing rendered it,
 * and nothing loaded analytics — so the product asked for permission to do a
 * thing it had stopped doing, while the marketing site's only measurement went
 * quiet. Both halves are here now, in the one place that knows about either.
 *
 * The key name is the old one on purpose. People have already answered this
 * question on osceguide.com, and a consent choice is not a detail to throw
 * away: re-asking is worse than sharing a name across two frontends that will
 * not exist at the same time.
 *
 * What is deliberately absent is Mixpanel. It needs a dependency this project
 * has not agreed to, and the legacy funnel events were a client-side call that
 * belongs next to the flows that raise them — the landing and the partner
 * capture — not in a provider that only loads a script tag.
 */

const CONSENT_KEY = "analytics-consent";
const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID ?? "G-57RJ52Q20T";

export function AnalyticsConsentGate({ children }: { children: ReactNode }) {
  const [consent, setConsent] = useState<"unknown" | "accepted" | "rejected">("unknown");

  useEffect(() => {
    const stored = localStorage.getItem(CONSENT_KEY);
    setConsent(stored === "accepted" ? "accepted" : stored === "rejected" ? "rejected" : "unknown");
  }, []);

  const decide = (enabled: boolean) => {
    setConsent(enabled ? "accepted" : "rejected");
  };

  return (
    <>
      {children}
      {consent === "accepted" ? (
        <>
          <Script async src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`} />
          <Script id="google-analytics">
            {`
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', '${GA_MEASUREMENT_ID}');
            `}
          </Script>
        </>
      ) : null}
      {consent === "unknown" ? <CookiesConsentModal setAnalyticsEnabled={decide} /> : null}
    </>
  );
}
