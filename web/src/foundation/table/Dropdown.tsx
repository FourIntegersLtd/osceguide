"use client";

import React, { useState } from "react";
import { cn } from "@/foundation/ui/cn";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
} from "@/foundation/ui/B2CPanelCard";
import {
  B2CSectionIconBadge,
  type B2CSectionIconTone,
} from "@/foundation/ui/B2CSectionIconBadge";

interface DropdownProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
  iconTone?: B2CSectionIconTone;
  defaultOpen?: boolean;
}

/**
 * Collapsible section shell. always sharp edges.
 * Curved cards belong inside the body (content), not on the expander chrome.
 */
function Dropdown({
  title,
  children,
  className = "",
  icon,
  iconTone = "primary",
  defaultOpen = false,
}: DropdownProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <B2CPanelCard className={cn("mt-0 !rounded-none", className)}>
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

export default Dropdown;
