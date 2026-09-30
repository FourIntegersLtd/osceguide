"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import {
  b2cButtonDanger,
  b2cButtonPrimary,
  b2cButtonCommit,
  b2cGhostButton,
  b2cFieldLabel,
  b2cGroupedRowTitle,
  b2cModalHelper,
  b2cModalTitle,
} from "@/foundation/ui/productTokens";
import type { B2CSectionIconBadgeSize } from "@/foundation/ui/B2CSectionIconBadge";
import {
  ModalBody,
  ModalIcon,
  ModalLead,
  ModalSectionBullets,
  type ModalTone,
} from "@/foundation/ui/ModalSection";

/**
 * Shared primitives for B2C modal bodies.
 *
 * The visual language is defined once in `ModalSection` and re-exported here,
 * so a modal needs a single import: lead header, tinted sections, accent
 * bullets, footnote, footer actions.
 */

export {
  ModalBandAnnotation,
  ModalBandPillMarker,
  ModalBandRow,
  ModalBandRowList,
  ModalBody,
  ModalFootnote,
  ModalIcon,
  ModalLead,
  ModalList,
  ModalListRow,
  ModalSection,
  ModalSectionBullets,
} from "@/foundation/ui/ModalSection";
export type { ModalTone } from "@/foundation/ui/ModalSection";

/** Alias of {@link ModalBody}. Every modal body owns the same vertical rhythm. */
export function ModalContent({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <ModalBody className={className}>{children}</ModalBody>;
}

export function ModalTitle({
  children,
  className = "",
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <h3 id={id} className={cn(b2cModalTitle, className)}>
      {children}
    </h3>
  );
}

export function ModalHelper({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <p className={cn(b2cModalHelper, className)}>{children}</p>;
}

export function ModalHeader({
  title,
  description,
  icon,
  iconTone = "primary",
  eyebrow,
  className = "",
}: {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  iconTone?: ModalTone;
  eyebrow?: string;
  className?: string;
}) {
  return (
    <ModalLead
      eyebrow={eyebrow}
      title={title}
      description={description}
      icon={icon}
      iconTone={iconTone}
      className={className}
    />
  );
}

export function ModalIconWell({
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
    <ModalIcon tone={tone} size={size} className={cn("mt-0.5", className)}>
      {children}
    </ModalIcon>
  );
}

export function ModalRow({
  icon,
  title,
  description,
  trailing,
  onClick,
  className = "",
}: {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  trailing?: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  const inner = (
    <>
      {icon ? (
        <ModalIconWell tone="primary" size="sm">
          {icon}
        </ModalIconWell>
      ) : null}
      <span className="min-w-0 flex-1">
        <span className={cn("block", b2cGroupedRowTitle)}>{title}</span>
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
          "flex w-full items-start gap-3 px-4 py-3.5 text-left transition hover:bg-b2c-surface-muted",
          className,
        )}
      >
        {inner}
      </button>
    );
  }

  return (
    <div className={cn("flex items-start gap-3 px-4 py-3.5", className)}>
      {inner}
    </div>
  );
}

export function ModalPrimaryButton({
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={cn(
        b2cButtonPrimary,
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/**
 * Black footer CTA for modals whose primary action commits something —
 * saves, confirms, creates, deletes-by-another-name.
 *
 * Deliberately a sibling of `ModalPrimaryButton` rather than a replacement for
 * it: plenty of modal footers are dismissals or acknowledgements, and flipping
 * the shared component would black out every modal in the app at once. Migrate
 * modals one at a time, and check the trigger behind the modal isn't already
 * black before you do.
 */
export function ModalCommitButton({
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={cn(
        b2cButtonCommit,
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function ModalSecondaryButton({
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={cn(
        b2cGhostButton,
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function ModalDangerButton({
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={cn(
        b2cButtonDanger,
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function ModalFooterActions({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col-reverse gap-2 pb-0.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end [&>button]:w-full sm:[&>button]:w-auto",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function ModalCallout({
  children,
  label,
  className = "",
}: {
  children: ReactNode;
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl bg-b2c-surface-muted px-4 py-3.5 sm:px-5 sm:py-4",
        className,
      )}
    >
      <p className="text-osce-meta leading-relaxed text-b2c-text-secondary">
        {label ? (
          <strong className="font-semibold text-osce-ink-900">{label}: </strong>
        ) : null}
        {children}
      </p>
    </div>
  );
}

export function ModalField({
  label,
  htmlFor,
  children,
  className = "",
}: {
  label: ReactNode;
  htmlFor?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={htmlFor} className={b2cFieldLabel}>
        {label}
      </label>
      {children}
    </div>
  );
}

export function ModalBullets({
  items,
  className = "",
  tone = "muted",
}: {
  items: ReactNode[];
  className?: string;
  /** `primary` for exam scripts and other long-form reading copy. */
  tone?: "muted" | "primary";
}) {
  if (tone === "primary") {
    return (
      <ul
        className={cn(
          "list-disc space-y-2 pl-5 marker:text-osce-accent",
          className,
        )}
      >
        {items.map((item, index) => (
          <li
            key={index}
            className="pl-0.5 text-osce-body leading-relaxed text-osce-ink-900"
          >
            {item}
          </li>
        ))}
      </ul>
    );
  }

  return <ModalSectionBullets items={items} className={className} />;
}