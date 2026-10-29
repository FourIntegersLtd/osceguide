"use client";

import type { ComponentProps } from "react";
import { SiteButtonLink } from "@/foundation/ui";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";

/** A site button link whose path keeps the visitor's partner attribution (and exam) on funnel links. */
export function PartnerLink({
  path,
  exam,
  ...props
}: Omit<ComponentProps<typeof SiteButtonLink>, "href"> & { path: string; exam?: string }) {
  const partner = usePartnerContext();
  return <SiteButtonLink href={partner.href(path, exam)} {...props} />;
}
