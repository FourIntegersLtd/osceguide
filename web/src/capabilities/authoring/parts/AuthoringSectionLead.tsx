"use client";

import type { ReactNode } from "react";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";

/** Staff console: action only. Workspace arms: lead copy + action. The action is a write, so a reader sees none. */
export function AuthoringSectionLead({
  children,
  action,
}: {
  children?: ReactNode;
  action: ReactNode;
}) {
  const chrome = useAuthoringChrome();
  const shown = useCanAuthor() ? action : null;

  if (chrome.b2c) {
    return <div className="flex justify-end">{shown}</div>;
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      {children ? <p className={`text-osce-body ${chrome.bodyMuted}`}>{children}</p> : null}
      {shown}
    </div>
  );
}
