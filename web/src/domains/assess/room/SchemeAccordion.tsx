"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { LuChevronDown } from "react-icons/lu";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { cn } from "@/foundation/ui/cn";
import { firstOpen, nextOpen, type SchemeDomain } from "@/domains/assess/room/schemeDomains";

/**
 * A marking scheme as one-open-at-a-time domains under a sticky header. The panel it sits in decides the
 * height; this scrolls inside it, so the page never grows with a long scheme.
 */
export function SchemeAccordion({
  title,
  domains,
  isDone,
  renderItem,
  status,
  footer,
}: {
  title: string;
  domains: SchemeDomain[];
  /** Whether an item has been marked; omit for a read-only scheme (no progress shown). */
  isDone?: (key: string) => boolean;
  renderItem?: (item: { key: string; label: string }, domain: SchemeDomain) => ReactNode;
  status?: ReactNode;
  /** After the last domain, inside the same scroll (the supervisor's peer marks). */
  footer?: ReactNode;
}) {
  const done = (key: string) => (isDone ? isDone(key) : false);
  const total = domains.reduce((sum, d) => sum + d.items.length, 0);
  const marked = domains.reduce((sum, d) => sum + d.items.filter((i) => done(i.key)).length, 0);
  const [open, setOpen] = useState<string | null>(() => firstOpen(domains, done));
  const rows = useRef<Record<string, HTMLElement | null>>({});
  const wasComplete = useRef(false);

  // A finished domain hands over to the next one with something left to mark.
  const current = domains.find((d) => d.id === open);
  const complete = Boolean(isDone && current && current.items.every((i) => done(i.key)));
  useEffect(() => {
    if (complete && !wasComplete.current && open) setOpen(nextOpen(domains, open, done));
    wasComplete.current = complete;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [complete, open]);

  function choose(id: string) {
    const next = open === id ? null : id;
    setOpen(next);
    if (next) requestAnimationFrame(() => rows.current[next]?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
  }

  if (domains.length === 0) return <p className={cn(assessMeta, "p-5")}>This station has no marking scheme to show.</p>;
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-osce-ink-100 px-4 py-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="m-0 text-assess-label font-medium text-osce-ink-900 max-lg:sr-only">{title}</h2>
          <div className="flex items-baseline gap-3" aria-live="polite">
            {status}
            {isDone ? <span className={assessMeta}>{marked} of {total} marked</span> : null}
          </div>
        </div>
        {isDone ? (
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-osce-ink-100" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={marked} aria-label="Marked so far">
            <div className="h-full rounded-full bg-osce-accent transition-[width] duration-200 motion-reduce:transition-none" style={{ width: `${total ? (marked / total) * 100 : 0}%` }} />
          </div>
        ) : null}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-width:thin]">
      <ol className="m-0 list-none p-0">
        {domains.map((domain) => {
          const isOpen = open === domain.id;
          const count = domain.items.filter((i) => done(i.key)).length;
          return (
            <li key={domain.id} ref={(el) => { rows.current[domain.id] = el; }} className="border-b border-osce-ink-100 last:border-b-0">
              <h3 className="m-0">
                <button
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => choose(domain.id)}
                  className="flex h-10 w-full items-center gap-2 px-4 text-left text-assess-desc font-medium text-osce-ink-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-osce-accent"
                >
                  <span className="min-w-0 flex-1 truncate">{domain.title}</span>
                  {isDone ? <span className={cn(assessMeta, "tabular-nums")}>{count}/{domain.items.length}</span> : null}
                  <LuChevronDown aria-hidden className={cn("h-4 w-4 shrink-0 text-osce-ink-500 transition-transform duration-150 motion-reduce:transition-none", isOpen && "rotate-180")} />
                </button>
              </h3>
              {isOpen ? (
                <ul className="m-0 flex list-none flex-col px-4 pb-3">
                  {domain.instructions ? <li className={cn(assessMeta, "pb-1")}>{domain.instructions}</li> : null}
                  {domain.items.map((item) => (
                    <li key={item.key} className="min-h-8 py-1 text-assess-desc text-osce-ink-700">
                      {renderItem ? renderItem(item, domain) : item.label}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          );
        })}
      </ol>
      {footer}
      </div>
    </div>
  );
}
