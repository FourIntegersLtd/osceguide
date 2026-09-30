"use client";

import type { ReactNode } from "react";
import { builderUi } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

export function TemplateBuilderShell({
  title,
  onTitleChange,
  titlePlaceholder = "Untitled template",
  meta,
  toolbarActions,
  subheader,
  children,
  flatChrome: _flatChrome = false,
}: {
  title?: string;
  onTitleChange?: (title: string) => void;
  titlePlaceholder?: string;
  meta?: ReactNode;
  toolbarActions?: ReactNode;
  /** Rendered full-width between the toolbar and the columns (narrow-screen section chips). */
  subheader?: ReactNode;
  children: ReactNode;
  /** @deprecated One palette serves both arms now. */
  flatChrome?: boolean;
}) {
  return (
    <div
      className={[
        "flex min-h-[560px] flex-col overflow-hidden rounded-2xl shadow-sm",
        builderUi.box,
        builderUi.surface,
      ].join(" ")}
    >
      <div
        className={[
          "flex items-center justify-between gap-3 px-5 py-3",
          builderUi.surface,
          builderUi.b,
        ].join(" ")}
      >
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {title !== undefined && onTitleChange ? (
            <input
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              className="min-w-0 flex-1 rounded-osce-md border-0 bg-transparent px-1 py-1 text-osce-body font-semibold text-ink-muted outline-none transition-colors placeholder:text-ink-subtle hover:bg-osce-canvas focus:bg-osce-canvas"
              placeholder={titlePlaceholder}
              aria-label="Template title"
            />
          ) : (
            <p className="text-osce-body font-semibold text-ink-muted">
              Template structure
            </p>
          )}
          {meta ? (
            <span className="hidden shrink-0 text-osce-caption text-ink-subtle sm:inline">
              {meta}
            </span>
          ) : null}
        </div>
        {toolbarActions ? (
          <div className="flex shrink-0 items-center gap-1">{toolbarActions}</div>
        ) : null}
      </div>
      {subheader}
      <div className="relative flex min-h-0 flex-1 items-stretch">{children}</div>
    </div>
  );
}
