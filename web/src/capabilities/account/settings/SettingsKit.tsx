import type { ComponentType, ReactNode } from "react";
import { cn } from "@/foundation/ui";

// The pieces every settings tab is drawn from beside the shared `Panel`: a list
// of rows with a grey icon tile, a switch and a status pill.

export function SettingsRows({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-osce-lg border border-border bg-surface [&>*+*]:border-t [&>*+*]:border-osce-border-light",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SettingsTile({
  icon: Icon,
  size = "sm",
}: {
  icon: ComponentType<{ className?: string }>;
  size?: "sm" | "md" | "lg";
}) {
  const box = size === "lg" ? "h-10 w-10" : size === "md" ? "h-9 w-9" : "h-8 w-8";
  return (
    <span
      className={cn("flex shrink-0 items-center justify-center rounded-osce-md bg-canvas text-ink-muted", box)}
      aria-hidden
    >
      <Icon className="h-4 w-4" />
    </span>
  );
}

export function SettingsRow({
  icon,
  title,
  meta,
  trailing,
  children,
}: {
  icon?: ComponentType<{ className?: string }>;
  title: ReactNode;
  meta?: ReactNode;
  trailing?: ReactNode;
  /** Anything that belongs under the row's text, such as an error. */
  children?: ReactNode;
}) {
  return (
    <div className="flex min-h-[54px] items-center gap-3 px-4 py-[9px]">
      {icon ? <SettingsTile icon={icon} /> : null}
      <div className="min-w-0 flex-1">
        <p className="text-osce-body font-medium leading-[19px] text-ink">{title}</p>
        {meta ? <p className="mt-[3px] text-osce-meta text-ink-muted">{meta}</p> : null}
        {children}
      </div>
      {trailing ? <div className="flex shrink-0 items-center gap-2">{trailing}</div> : null}
    </div>
  );
}

const PILL_DOT = {
  ok: "bg-success",
  warning: "bg-warning",
  accent: "bg-accent",
  neutral: "bg-ink-subtle",
} as const;

export type PillTone = keyof typeof PILL_DOT;

/** The canvas pill: grey, with a dot that carries the status. */
export function StatusPill({ tone = "neutral", children }: { tone?: PillTone; children: ReactNode }) {
  return (
    <span className="inline-flex h-[22px] w-fit shrink-0 items-center gap-1.5 whitespace-nowrap rounded-osce-sm bg-canvas px-2 text-osce-caption font-medium text-ink">
      <span className={cn("h-1.5 w-1.5 rounded-full", PILL_DOT[tone])} aria-hidden />
      {children}
    </span>
  );
}

/** A field label over its control (canvas `.lab`). */
export const settingsLabel = "mb-1.5 block text-osce-meta font-medium text-ink";
/** The muted sentence that explains a card or a field (canvas `.sub`, `.meta`). */
export const settingsSub = "text-osce-body text-ink-muted";
export const settingsMeta = "text-osce-meta text-ink-muted";
