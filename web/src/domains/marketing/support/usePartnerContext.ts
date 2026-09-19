"use client";

import { useCallback, useEffect, useState } from "react";
import { parseReferralParams } from "@/domains/marketing/support/parseReferralParams";
import {
  readPartnerContext,
  savePartnerContext,
  type StoredPartnerContext,
} from "@/domains/marketing/support/partnerContextStorage";
import { withReferralParams } from "@/domains/marketing/support/withReferralParams";

/**
 * Exposes the partner a visitor arrived from (URL params first, then the
 * session-stored context) and an `href()` helper that keeps attribution and
 * exam on every funnel link.
 */
export function usePartnerContext() {
  const [context, setContext] = useState<StoredPartnerContext | null>(null);
  const [search, setSearch] = useState("");

  // URL and sessionStorage are only readable after hydration.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (typeof window === "undefined") return;
    setSearch(window.location.search);
    const parsed = parseReferralParams({
      host: window.location.host,
      pathname: window.location.pathname,
      search: window.location.search,
    });
    if (parsed) savePartnerContext(parsed);
    setContext(readPartnerContext());
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const href = useCallback(
    (path: string, appType?: string | null) =>
      withReferralParams(path, { search, context, appType }),
    [search, context],
  );

  return {
    partner: context?.partner ?? null,
    exam: context?.exam ?? null,
    isPartnerVisit: context !== null,
    href,
  };
}
