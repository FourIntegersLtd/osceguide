"use client";

import { useState, type ReactNode } from "react";
import { HiChevronDown } from "react-icons/hi2";
import { builderUi } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

/** Collapsed-by-default disclosure for secondary settings in the inspector. */
export function MoreOptions({
  label = "More options",
  defaultOpen = false,
  children,
}: {
  label?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`-mx-1 rounded-xl px-1 ${open ? "bg-osce-canvas/70 pb-3" : ""}`}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center justify-between rounded-osce-lg px-2 py-2 text-left text-osce-caption font-semibold text-ink-muted transition-colors hover:bg-osce-canvas hover:text-ink-muted ${builderUi.focusRing}`}
      >
        {label}
        <HiChevronDown
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>
      {open ? <div className="mt-1 space-y-4 px-2">{children}</div> : null}
    </div>
  );
}

export const inspectorLabel = `mb-1.5 block ${builderUi.eyebrow}`;
export const inspectorHint = "mt-1.5 text-osce-caption leading-snug text-ink-subtle";
