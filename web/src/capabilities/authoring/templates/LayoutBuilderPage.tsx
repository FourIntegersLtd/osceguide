"use client";

import type { ReactNode } from "react";
import { B2CPageHeader } from "@/foundation/ui";

/** The station layout builder's page (LayoutBuilder board): the board header with a back link, then the screen's own cards. */
export function LayoutBuilderPage({
  title,
  subtitle,
  backHref,
  backLabel = "Templates",
  children,
}: {
  title: string;
  subtitle?: string;
  backHref: string;
  backLabel?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex w-full max-w-assess-page flex-col gap-6 pb-8" data-testid="layout-builder-page">
      <B2CPageHeader
        board
        action={<span aria-hidden />}
        className="!mb-0"
        wideSubtitle
        eyebrow="Station layouts"
        title={title}
        subtitle={subtitle}
        back={{ href: backHref, label: backLabel }}
      />
      {children}
    </div>
  );
}
