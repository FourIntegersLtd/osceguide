import type { ReactNode } from "react";

/** The side panel's frame inside the room card: a quiet heading over a body that scrolls on its own. */
export function SidePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <h2 className="m-0 shrink-0 border-b border-osce-ink-100 px-4 py-3 max-lg:sr-only text-assess-label font-medium text-osce-ink-900">{title}</h2>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-width:thin]">{children}</div>
    </div>
  );
}
