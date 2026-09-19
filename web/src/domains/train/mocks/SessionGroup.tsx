"use client";

import { useState, type ReactNode } from "react";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  B2CSectionIconBadge,
  cn,
} from "@/foundation/ui";
import type { B2CSectionIconTone } from "@/foundation/ui";

/**
 * A collapsible section, sharp-edged.
 *
 * The retiring client kept this in `components/shared/table/Dropdown`, where
 * it was neither a dropdown nor anything to do with tables. It is here rather
 * than in `foundation/ui` because the sessions list is its only caller; the
 * moment a second screen wants one it moves down a tier.
 */
export function SessionGroup({
  title,
  icon,
  iconTone = "primary",
  defaultOpen = false,
  children,
}: {
  title: string;
  icon?: ReactNode;
  iconTone?: B2CSectionIconTone;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <B2CPanelCard className={cn("mt-0 !rounded-none")}>
      <button
        type="button"
        className="w-full text-left"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
      >
        <B2CPanelCardHeader className="cursor-pointer select-none rounded-none hover:bg-b2c-secondary">
          <span className="flex min-w-0 flex-1 items-center gap-2.5">
            {icon ? (
              <B2CSectionIconBadge tone={iconTone} size="sm" className="shrink-0">
                {icon}
              </B2CSectionIconBadge>
            ) : null}
            <span className="truncate">{title}</span>
          </span>
          <span className="shrink-0 text-osce-body leading-none text-b2c-text-muted">
            {isOpen ? "−" : "+"}
          </span>
        </B2CPanelCardHeader>
      </button>
      {isOpen ? <B2CPanelCardBody>{children}</B2CPanelCardBody> : null}
    </B2CPanelCard>
  );
}
