"use client";

import type { ComponentType, ReactNode } from "react";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { boardBtn } from "@/foundation/ui/boardKit";

/**
 * A section's top-right action: the board's text button on the organisation arms, the icon
 * button of the staff console elsewhere.
 */
export function AuthoringLeadButton({
  primary = false,
  icon: Icon,
  small = false,
  onClick,
  children,
}: {
  primary?: boolean;
  icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  /** The board's `.btn.sm` rather than `.btn`. */
  small?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  const chrome = useAuthoringChrome();
  if (!chrome.b2c) {
    return (
      <button type="button" onClick={onClick} className={boardBtn(primary ? "primary" : "default", small)}>
        {children}
      </button>
    );
  }
  return (
    <AuthoringButton variant={primary ? "commit" : "secondary"} size="sm" className="gap-2" onClick={onClick}>
      {Icon ? <Icon className="h-4 w-4 shrink-0" aria-hidden /> : null}
      {children}
    </AuthoringButton>
  );
}
