import Link from "next/link";
import type { ComponentType, ReactNode } from "react";
import { HiChevronRight } from "react-icons/hi2";
import { cardScrollBody } from "@/foundation/ui/Card";
import { cn } from "@/foundation/ui/cn";
import {
  b2cGroupedRow,
  b2cGroupedRowSubtitle,
  b2cGroupedRowTitle,
  b2cGroupedShell,
  b2cMonoEyebrow,
} from "@/foundation/ui/productTokens";

/**
 * The canvas's grouped list: a sentence-case label (and an optional link) over
 * a card of rows. Used for "What to work on", "Recent stations", sessions,
 * debriefs and every other list of things you open.
 */
export function B2CGroupedSection({
  eyebrow,
  action,
  children,
  className,
  id,
}: {
  id?: string;
  eyebrow: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} className={cn("min-w-0", className)}>
      <div className="flex items-baseline justify-between gap-3 px-1 pb-2">
        <h2 className={b2cMonoEyebrow}>{eyebrow}</h2>
        {action ? <div className="text-osce-body font-medium">{action}</div> : null}
      </div>
      <div className={cn(b2cGroupedShell, cardScrollBody)}>{children}</div>
    </section>
  );
}

type RowProps = {
  title: ReactNode;
  meta?: ReactNode;
  icon?: ComponentType<{ className?: string }>;
  /** Replaces the icon square, such as a date tile. */
  leading?: ReactNode;
  trailing?: ReactNode;
  /** The row for what is open now, such as the episode that is playing. */
  active?: boolean;
  className?: string;
};

function RowBody({ title, meta, icon: Icon, leading, trailing, active, chevron }: RowProps & { chevron: boolean }) {
  return (
    <>
      {leading ?? null}
      {Icon && !leading ? (
        <span
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-md",
            active ? "bg-osce-accent text-white" : "bg-b2c-surface-muted text-osce-ink-700",
          )}
        >
          <Icon className="h-4 w-4" />
        </span>
      ) : null}
      <span className="min-w-0 flex-1">
        <span className={cn("block truncate", b2cGroupedRowTitle)}>{title}</span>
        {meta ? <span className={cn("block truncate", b2cGroupedRowSubtitle)}>{meta}</span> : null}
      </span>
      {trailing}
      {chevron ? <HiChevronRight className="h-4 w-4 shrink-0 text-osce-ink-400" aria-hidden /> : null}
    </>
  );
}

/** A row you open: a link with a chevron. */
export function B2CGroupedRowLink({
  href,
  scroll,
  className,
  ...row
}: RowProps & { href: string; scroll?: boolean }) {
  return (
    <Link
      href={href}
      scroll={scroll}
      aria-current={row.active ? "page" : undefined}
      className={cn(b2cGroupedRow, className)}
    >
      <RowBody {...row} chevron />
    </Link>
  );
}

/** A row that only says something (no destination), or acts through `onClick`. */
export function B2CGroupedRow({ onClick, className, ...row }: RowProps & { onClick?: () => void }) {
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(b2cGroupedRow, "w-full text-left", className)}>
        <RowBody {...row} chevron />
      </button>
    );
  }
  return (
    <div className={cn(b2cGroupedRow, "hover:bg-transparent", className)}>
      <RowBody {...row} chevron={false} />
    </div>
  );
}
