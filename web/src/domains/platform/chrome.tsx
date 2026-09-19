"use client";

import type { ReactNode } from "react";
import { Badge, Button, Card, cn, productTokens as t } from "@/foundation/ui";
import { statusTone } from "@/domains/platform/support";

/**
 * Console layout primitives — B2C card chrome and osce typography (not semantic ink/black).
 */

/** A titled block. The console is a stack of these on every screen. */
export function Section({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="min-w-0">
          <h2 className={t.b2cSectionTitle}>{title}</h2>
          {description ? <p className={`mt-0.5 ${t.b2cBodyTextMuted}`}>{description}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

/** A card holding a divided list. Every listing on the console is one. */
export function RowList({ children }: { children: ReactNode }) {
  return (
    <Card>
      <ul className="divide-y divide-b2c-border">{children}</ul>
    </Card>
  );
}

export function Row({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <li className={cn("flex flex-wrap items-center justify-between gap-3 px-5 py-3", className)}>
      {children}
    </li>
  );
}

/**
 * An organisation's status, coloured by whether its members can sign in.
 *
 * `trial` is amber rather than green on purpose: it permits access and it is
 * also the state somebody is meant to act on before it lapses.
 */
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTone(status)}>{status || "active"}</Badge>;
}

/**
 * A field the backend takes and does not give back.
 *
 * Used on the contract dates. Writing a value you cannot read back is worth
 * saying out loud on the screen rather than leaving an administrator to wonder
 * whether the save worked.
 */
export function WriteOnlyNote({ children }: { children: ReactNode }) {
  return <p className="text-osce-meta text-b2c-text-muted">{children}</p>;
}

/** Cursor paging, as the one button every listing here uses. */
export function LoadMore({
  cursor,
  busy,
  onLoad,
}: {
  cursor: string | null | undefined;
  busy: boolean;
  onLoad: () => void;
}) {
  if (!cursor) return null;
  return (
    <div className="flex justify-center">
      <Button variant="secondary" size="sm" onClick={onLoad} disabled={busy}>
        {busy ? "Loading…" : "Load more"}
      </Button>
    </div>
  );
}
