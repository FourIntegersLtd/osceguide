import Link from "next/link";
import type { ReactNode } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { boardCard, boardRow } from "@/foundation/ui/boardKit";

/**
 * The pieces the five Trainee boards (docs/institution-overhaul/boards/{Trainee,TraineeSitting,TraineeResult,
 * TraineeReview,SelfPractice}.dc.html) repeat: the page column, the head, a hero, a card of rows and a row.
 * Sizes and colours come from the assess tokens; nothing here reads data.
 */

/** The board's `.page`; `label` names the region for the spec and for screen readers. */
export function TraineePage({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <section aria-label={label} className={t.assessPage}>
      {children}
    </section>
  );
}

/** The board's `.head`: eyebrow, title and optional description on the left, `.acts` on the right. */
export function TraineeHead({
  eyebrow,
  title,
  desc,
  acts,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  desc?: ReactNode;
  acts?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow ? <div className={t.assessEyebrow}>{eyebrow}</div> : null}
        <h1 className={t.assessTitle}>{title}</h1>
        {desc ? <p className={cn(t.assessDesc, "m-0")}>{desc}</p> : null}
      </div>
      {acts ? (
        <div className="flex flex-wrap items-center gap-2.5">{acts}</div>
      ) : null}
    </div>
  );
}

/** The board's `.hero` (and `.hero.live` when `live`): a title, one line and the one action. */
export function TraineeHero({
  eyebrow,
  title,
  size = "lg",
  live = false,
  action,
  children,
  label,
}: {
  eyebrow: ReactNode;
  title: ReactNode;
  size?: "xl" | "lg" | "md";
  live?: boolean;
  action?: ReactNode;
  children?: ReactNode;
  label?: string;
}) {
  return (
    <section
      aria-label={label}
      className={cn(
        "flex flex-wrap items-center justify-between gap-5 rounded-panel border p-6",
        live
          ? "border-osce-accent bg-osce-accent-muted/40"
          : "border-osce-border bg-osce-surface",
      )}
    >
      <div>
        <div className={t.assessEyebrow}>{eyebrow}</div>
        <h2
          className={cn(
            "mt-1 font-semibold",
            size === "xl"
              ? "text-[24px]"
              : size === "lg"
                ? "text-[22px]"
                : "text-assess-h2",
          )}
        >
          {title}
        </h2>
        {children ? <div className={t.assessMeta}>{children}</div> : null}
      </div>
      {action}
    </section>
  );
}

/** The board's `.card` with its first row holding the card's `h2`. */
export function TraineeList({
  title,
  children,
  label,
  untitled,
}: {
  title: ReactNode;
  children: ReactNode;
  label?: string;
  /** The board draws rows only: keep the heading for screen readers, not as a row. */
  untitled?: boolean;
}) {
  return (
    <section aria-label={label} className={cn(boardCard, "overflow-hidden")}>
      {untitled ? (
        <h2 className="sr-only">{title}</h2>
      ) : (
        <div className={cn(boardRow, "border-t-0")}>
          <h2 className="text-assess-desc font-semibold">{title}</h2>
        </div>
      )}
      {children}
    </section>
  );
}

/** The board's `.card.pad`. */

/** The board's `.row` with a title and meta line; `lead` is what sits on the right of it. */
function TraineeRowBody({
  title,
  meta,
  children,
}: {
  title: ReactNode;
  meta?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <>
      <span className="min-w-0 flex-1 leading-[1.35]">
        {title}
        {meta ? <div className={t.assessMeta}>{meta}</div> : null}
      </span>
      {children}
    </>
  );
}

export function TraineeRowLink({
  href,
  title,
  meta,
  children,
}: {
  href: string;
  title: ReactNode;
  meta?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <Link href={href} className={cn(boardRow, "hover:bg-osce-surface-inset")}>
      <TraineeRowBody title={title} meta={meta}>
        {children}
      </TraineeRowBody>
    </Link>
  );
}

export function TraineeRow({
  title,
  meta,
  children,
}: {
  title: ReactNode;
  meta?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className={boardRow}>
      <TraineeRowBody title={title} meta={meta}>
        {children}
      </TraineeRowBody>
    </div>
  );
}
