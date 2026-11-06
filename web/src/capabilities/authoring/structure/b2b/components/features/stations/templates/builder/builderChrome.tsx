"use client";

import {
  createContext,
  useContext,
  type ReactNode,
} from "react";
import type { StationSectionAudience } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

/**
 * The builder's visual vocabulary, on the canonical `osce-*` tokens.
 *
 * Deliberately not `b2b-*`: those are CSS variables the institution layout
 * defines under `.b2b-app`, and platform-web never defines them, so a
 * `border-border` there resolves to `currentColor` — a black hairline.
 * `osce-*` is defined by both apps, so one palette renders the same in each.
 */
export const builderUi = {
  box: "border border-osce-border",
  b: "border-b border-osce-border",
  t: "border-t border-osce-border",
  r: "border-r border-osce-border",
  l: "border-l border-osce-border",
  rule: "bg-osce-border",
  divide: "divide-y divide-osce-border-light",
  canvas: "bg-osce-canvas",
  surface: "bg-osce-surface",
  /** Grey ink, never black: 700 for labels, 500 secondary, 400 meta. */
  text: "text-ink-muted",
  textSecondary: "text-ink-muted",
  textMuted: "text-ink-subtle",
  eyebrow:
    "text-osce-micro font-semibold uppercase tracking-[0.08em] text-ink-subtle",
  selectedRow: "bg-osce-accent-muted ring-1 ring-inset ring-osce-accent-subtle",
  hoverRow: "hover:bg-osce-canvas",
  focusRing:
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent/25",
} as const;

/** Pastel tones cycled across sections so moving between them is unmistakable. */
export type BuilderTone =
  | "primary"
  | "emerald"
  | "amber"
  | "rose"
  | "violet"
  | "history";

const TONES: BuilderTone[] = [
  "primary",
  "emerald",
  "violet",
  "amber",
  "history",
  "rose",
];

/** Station sections are coloured by who reads them, so the colour means something. */
export const toneForAudience: Record<StationSectionAudience, BuilderTone> = {
  patient: "primary",
  candidate: "emerald",
  examiner: "amber",
  faculty: "violet",
};

export function toneForIndex(index: number): BuilderTone {
  return TONES[((index % TONES.length) + TONES.length) % TONES.length] ?? "primary";
}

export const toneClass: Record<
  BuilderTone,
  { badge: string; band: string; dot: string; ring: string; text: string }
> = {
  primary: {
    badge: "bg-osce-accent-muted text-osce-accent",
    band: "bg-osce-accent-muted",
    dot: "bg-osce-accent",
    ring: "ring-osce-accent-subtle",
    text: "text-osce-accent",
  },
  emerald: {
    badge: "bg-osce-success-bg text-osce-success-text",
    band: "bg-osce-success-bg",
    dot: "bg-osce-success-icon",
    ring: "ring-osce-success-border",
    text: "text-osce-success-text",
  },
  amber: {
    badge: "bg-osce-warning-bg text-osce-warning-text",
    band: "bg-osce-warning-bg",
    dot: "bg-osce-warning-icon",
    ring: "ring-osce-warning-border",
    text: "text-osce-warning-text",
  },
  rose: {
    badge: "bg-osce-danger-bg text-osce-danger-text",
    band: "bg-osce-danger-bg",
    dot: "bg-osce-danger-icon",
    ring: "ring-osce-danger-border",
    text: "text-osce-danger-text",
  },
  violet: {
    badge: "bg-osce-tone-reasoning-bg text-osce-tone-reasoning-text",
    band: "bg-osce-tone-reasoning-bg",
    dot: "bg-osce-tone-reasoning-text",
    ring: "ring-osce-tone-reasoning-border",
    text: "text-osce-tone-reasoning-text",
  },
  history: {
    badge: "bg-osce-tone-history-bg text-osce-tone-history-text",
    band: "bg-osce-tone-history-bg",
    dot: "bg-osce-tone-history-text",
    ring: "ring-osce-tone-history-border",
    text: "text-osce-tone-history-text",
  },
};

const badgeSize = {
  xs: "h-6 w-6 rounded-osce-md [&>svg]:h-3.5 [&>svg]:w-3.5",
  sm: "h-8 w-8 rounded-osce-lg [&>svg]:h-4 [&>svg]:w-4",
  md: "h-9 w-9 rounded-osce-lg [&>svg]:h-[18px] [&>svg]:w-[18px]",
  lg: "h-11 w-11 rounded-xl [&>svg]:h-5 [&>svg]:w-5",
} as const;

/** Tinted square icon tile — the Apple Settings / B2C section-badge idiom. */
export function ToneBadge({
  tone = "primary",
  size = "sm",
  className = "",
  children,
}: {
  tone?: BuilderTone;
  size?: keyof typeof badgeSize;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={[
        "inline-flex shrink-0 items-center justify-center transition-colors",
        badgeSize[size],
        toneClass[tone].badge,
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}

/* Compatibility: older call sites read hairline classes from a context. */

type BuilderChrome = {
  box: string;
  b: string;
  r: string;
  l: string;
  t: string;
  rule: string;
};

const CHROME: BuilderChrome = {
  box: builderUi.box,
  b: builderUi.b,
  r: builderUi.r,
  l: builderUi.l,
  t: builderUi.t,
  rule: builderUi.rule,
};

const BuilderChromeContext = createContext<BuilderChrome>(CHROME);

/** Hands the builder its colours and borders. One `osce-*` palette serves both arms. */
export function BuilderChromeProvider({ children }: { children: ReactNode }) {
  return (
    <BuilderChromeContext.Provider value={CHROME}>
      {children}
    </BuilderChromeContext.Provider>
  );
}

export function useBuilderChrome(): BuilderChrome {
  return useContext(BuilderChromeContext);
}
