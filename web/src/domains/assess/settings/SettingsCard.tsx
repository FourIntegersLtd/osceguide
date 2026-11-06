import type { ReactNode } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { boardPadWide } from "@/foundation/ui/boardKit";

/** The board's `h2`: 16px (`assess-desc`), not the body text size the shared `h2` uses. */
export const cardTitle = "m-0 text-assess-desc font-semibold !leading-[normal] text-osce-ink-900";

/**
 * The Settings board's `.card.pad`: a title, one muted line, then the card's own content. The vertical rhythm
 * is the assess form scale (DESIGN.md "Spacing rhythm and quiet selection"): 16px between parts, and fields
 * in an `assessFormStack` (28px apart, label 8px above its control).
 */
export function SettingsCard({ title, lead, children, tone }: { title: string; lead?: ReactNode; children?: ReactNode; tone?: "danger" }) {
  return (
    <section className={boardPadWide}>
      <h2 className={cn(cardTitle, tone === "danger" && "text-osce-danger-text")}>{title}</h2>
      {lead ? <p className={cn(t.assessMeta, "m-0")}>{lead}</p> : null}
      {children}
    </section>
  );
}

/** A line inside a settings card: text on the left, its state or action on the right. */
export function StateRow({ first = false, children }: { first?: boolean; children: ReactNode }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-4 px-0 py-4 text-assess-label text-osce-ink-900", !first && "border-t border-osce-border-light")}>
      {children}
    </div>
  );
}
