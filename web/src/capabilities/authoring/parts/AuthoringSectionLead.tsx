"use client";

import type { ReactNode } from "react";
import { boardActs, boardMeta } from "@/capabilities/authoring/parts/boardUi";
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
    <div className="flex flex-wrap justify-between gap-3">
      {children ? <div className={`${boardMeta} min-w-0 flex-1 basis-[240px]`}>{children}</div> : null}
      {shown ? <div className={`${boardActs} shrink-0`}>{shown}</div> : null}
    </div>
  );
}
