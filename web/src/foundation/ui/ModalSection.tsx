"use client";

import type { ReactNode } from "react";
import {
  B2CBandPill,
  type B2CBandVariant,
} from "@/foundation/ui/BandPill";
import { B2CMonoEyebrow } from "@/foundation/ui/B2CMonoEyebrow";
import { b2cModalHelper, b2cModalTitle } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import {
  B2CSectionIconBadge,
  type B2CSectionIconBadgeSize,
  type B2CSectionIconTone,
} from "@/foundation/ui/B2CSectionIconBadge";

/**
 * Canonical modal body language, lifted from the SCA dashboard about modals.
 *
 * Every modal body reads the same way:
 *   ModalBody > ModalLead (icon + eyebrow + title + description)
 *             > ModalSection (label + tinted, borderless surface)
 *             > ModalFootnote (hairline rule + quiet closing line)
 *
 * Sections are tinted surfaces, never bordered cards — a modal is already a
 * card, so a second border inside it reads as chrome on chrome.
 */

export type ModalTone =
  | "primary"
  | "competent"
  | "developing"
  | "development"
  | "violet"
  | "teal"
  | "amber"
  | "rose"
  | "sky"
  | "indigo"
  | "emerald"
  | "orange"
  | "muted";

function toneToBadge(tone: ModalTone): B2CSectionIconTone {
  switch (tone) {
    case "competent":
    case "emerald":
      return "emerald";
    case "developing":
    case "amber":
    case "orange":
      return "amber";
    case "development":
    case "rose":
      return "rose";
    case "violet":
    case "indigo":
      return "violet";
    case "teal":
    case "sky":
      return "sky";
    default:
      return "primary";
  }
}

const sectionTintClass: Partial<Record<ModalTone, string>> = {
  primary: "bg-osce-accent-muted/40",
  competent: "bg-osce-band-competentBg/50",
  emerald: "bg-osce-band-competentBg/50",
  developing: "bg-osce-band-developingBg/50",
  development: "bg-osce-band-developmentBg/50",
  violet: "bg-osce-tone-reasoning-bg/80",
  indigo: "bg-osce-tone-reasoning-bg/80",
  teal: "bg-osce-tone-examination-bg/80",
  amber: "bg-osce-warning-bg/80",
  orange: "bg-osce-warning-bg/80",
  rose: "bg-osce-band-developmentBg/50",
  sky: "bg-osce-accent-muted/80",
  muted: "bg-b2c-surface-muted",
};

/** Tinted square icon chip. The one icon holder for modal bodies. */
export function ModalIcon({
  children,
  tone = "primary",
  size = "md",
  className = "",
}: {
  children: ReactNode;
  tone?: ModalTone;
  size?: B2CSectionIconBadgeSize;
  className?: string;
}) {
  return (
    <B2CSectionIconBadge
      tone={toneToBadge(tone)}
      size={size}
      className={className}
    >
      {children}
    </B2CSectionIconBadge>
  );
}

/** Modal body scroll container. Owns the rhythm between sections. */
export function ModalBody({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "min-w-0 w-full max-w-full space-y-7 text-osce-body",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** The one modal header: icon well, optional eyebrow, title, description. */
export function ModalLead({
  eyebrow,
  title,
  description,
  icon,
  iconTone = "primary",
  id,
  className = "",
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  iconTone?: ModalTone;
  id?: string;
  className?: string;
}) {
  return (
    <header className={cn("flex items-start gap-3.5", className)}>
      {icon ? (
        <ModalIcon tone={iconTone} size="lg" className="mt-0.5">
          {icon}
        </ModalIcon>
      ) : null}
      <div className="min-w-0 flex-1 space-y-1.5">
        {eyebrow && eyebrow !== title ? (
          <B2CMonoEyebrow>{eyebrow}</B2CMonoEyebrow>
        ) : null}
        <h2 id={id} className={b2cModalTitle}>
          {title}
        </h2>
        {description ? <p className={b2cModalHelper}>{description}</p> : null}
      </div>
    </header>
  );
}

/** Labelled, tinted, borderless block. The only grouping device in a modal. */
export function ModalSection({
  title,
  icon,
  iconTone = "primary",
  tint = "muted",
  children,
  className = "",
  bodyClassName = "",
}: {
  title?: ReactNode;
  icon?: ReactNode;
  iconTone?: ModalTone;
  tint?: ModalTone;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("space-y-2.5", className)}>
      {title ? (
        <div className="flex items-center gap-2">
          {icon ? (
            <ModalIcon tone={iconTone} size="sm">
              {icon}
            </ModalIcon>
          ) : null}
          <h3 className="text-osce-meta font-semibold text-osce-ink-900">
            {title}
          </h3>
        </div>
      ) : null}
      <div
        className={cn(
          "rounded-xl px-4 py-3.5 sm:px-5 sm:py-4",
          sectionTintClass[tint] ?? sectionTintClass.muted,
          bodyClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
}

/** Hairline-divided stack of ModalListRow. Lives inside a ModalSection. */
export function ModalList({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("divide-y divide-b2c-border-light/80", className)}>
      {children}
    </div>
  );
}

export function ModalListRow({
  icon,
  iconTone = "primary",
  marker,
  title,
  description,
  trailing,
  onClick,
  className = "",
}: {
  icon?: ReactNode;
  iconTone?: ModalTone;
  marker?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  trailing?: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  const leading =
    marker ?? (icon ? <ModalIcon tone={iconTone}>{icon}</ModalIcon> : null);

  const inner = (
    <>
      {leading ? <span className="mt-0.5 shrink-0">{leading}</span> : null}
      <span className="min-w-0 flex-1">
        <span className="block text-osce-body font-medium text-osce-ink-900">
          {title}
        </span>
        {description ? (
          <span className="mt-0.5 block text-osce-meta leading-relaxed text-b2c-text-secondary">
            {description}
          </span>
        ) : null}
      </span>
      {trailing}
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "flex w-full items-start gap-3 py-3 text-left transition first:pt-0 last:pb-0 hover:opacity-80",
          className,
        )}
      >
        {inner}
      </button>
    );
  }

  return (
    <div
      className={cn(
        "flex items-start gap-3 py-3 first:pt-0 last:pb-0",
        className,
      )}
    >
      {inner}
    </div>
  );
}

/** Accent-dot or numbered list. Lives inside a ModalSection. */
export function ModalSectionBullets({
  items,
  numbered = false,
  className = "",
}: {
  items: ReactNode[];
  numbered?: boolean;
  className?: string;
}) {
  return (
    <ul className={cn("space-y-3", className)}>
      {items.map((item, index) => (
        <li key={index} className="flex items-start gap-3">
          {numbered ? (
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-osce-accent-muted text-osce-caption font-semibold text-osce-accent"
              aria-hidden
            >
              {index + 1}
            </span>
          ) : (
            <span
              className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-osce-accent/50"
              aria-hidden
            />
          )}
          <span className="min-w-0 text-osce-meta leading-relaxed text-b2c-text-secondary">
            {item}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Quiet closing line above the fold. One per modal, last. */
export function ModalFootnote({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "border-t border-b2c-border-light pt-4 text-osce-meta leading-relaxed text-b2c-text-muted",
        className,
      )}
    >
      {children}
    </p>
  );
}

const bandSurfaceClass: Record<B2CBandVariant, string> = {
  competent: "bg-osce-band-competentBg",
  developing: "bg-osce-band-developingBg",
  development: "bg-osce-band-developmentBg",
};

const bandTitleClass: Record<B2CBandVariant, string> = {
  competent: "text-osce-band-competent",
  developing: "text-osce-band-developing",
  development: "text-osce-band-development",
};

const bandRowSurfaceClass: Record<B2CBandVariant, string> = {
  competent: "bg-osce-band-competentBg border-osce-band-competentBorder",
  developing: "bg-osce-band-developingBg border-osce-band-developingBorder",
  development: "bg-osce-band-developmentBg border-osce-band-developmentBorder",
};

export function ModalBandPillMarker({ variant }: { variant: B2CBandVariant }) {
  return (
    <span className="inline-flex mt-0.5">
      <B2CBandPill variant={variant} compact />
    </span>
  );
}

export function ModalBandAnnotation({
  variant,
  title,
  description,
}: {
  variant: B2CBandVariant;
  title?: string;
  description: ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-xl px-4 py-4 sm:px-5 sm:py-4",
        bandSurfaceClass[variant],
      )}
    >
      <div className="mb-2.5">
        <B2CBandPill variant={variant} label={title} />
      </div>
      <p className="text-osce-body leading-relaxed text-b2c-text-secondary">
        {description}
      </p>
    </div>
  );
}

/** Band-coloured row: pill, tinted surface, and title in band colour. */
export function ModalBandRow({
  variant,
  title,
  description,
}: {
  variant: B2CBandVariant;
  title: ReactNode;
  description?: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border px-3 py-3 sm:px-3.5",
        bandRowSurfaceClass[variant],
      )}
    >
      <ModalBandPillMarker variant={variant} />
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-osce-body font-semibold",
            bandTitleClass[variant],
          )}
        >
          {title}
        </p>
        {description ? (
          <p className="mt-0.5 text-osce-meta leading-relaxed text-b2c-text-secondary">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function ModalBandRowList({ children }: { children: ReactNode }) {
  return <div className="space-y-2">{children}</div>;
}