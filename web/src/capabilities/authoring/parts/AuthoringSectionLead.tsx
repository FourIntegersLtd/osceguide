"use client";

import type { ReactNode } from "react";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";

/** Staff console: action only. Workspace arms: lead copy + action. */
export function AuthoringSectionLead({
  children,
  action,
}: {
  children?: ReactNode;
  action: ReactNode;
}) {
  const chrome = useAuthoringChrome();

  if (chrome.b2c) {
    return <div className="flex justify-end">{action}</div>;
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      {children ? <p className={`text-osce-body ${chrome.bodyMuted}`}>{children}</p> : null}
      {action}
    </div>
  );
}
