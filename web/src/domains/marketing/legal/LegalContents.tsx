"use client";

import { useEffect, useState } from "react";

type Entry = { id: string; text: string };

function slug(text: string, index: number): string {
  const base = text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `legal-${index}-${base || "section"}`;
}

/**
 * "On this page": built from the real `h2` headings of the reading column
 * (`#legal-body`), so it can never drift from the text. Headings without an id
 * get one. The heading in view is marked as the current one.
 */
export function LegalContents() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [current, setCurrent] = useState("");

  useEffect(() => {
    const headings = Array.from(document.querySelectorAll<HTMLElement>("#legal-body h2"));
    const found = headings.map((h, i) => {
      // Section ids are kept for old deep links; the heading gets its own, unique, id.
      if (!h.id) h.id = slug(h.textContent ?? "", i);
      return { id: h.id, text: (h.textContent ?? "").trim() };
    });
    // The DOM is only readable after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEntries(found);
    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (hits) => {
        const top = hits.filter((h) => h.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (top) setCurrent(top.target.id);
      },
      { rootMargin: "-80px 0px -65% 0px" },
    );
    headings.forEach((h) => observer.observe(h));
    return () => observer.disconnect();
  }, []);

  if (entries.length === 0) return null;

  const list = (
    <ol className="space-y-0.5 text-sm">
      {entries.map((e) => (
        <li key={e.id}>
          <a
            href={`#${e.id}`}
            aria-current={current === e.id ? "location" : undefined}
            className={`block rounded-md px-3 py-1.5 transition-colors hover:text-site-brand ${
              current === e.id ? "bg-site-pale font-semibold text-site-brand" : "text-site-muted"
            }`}
          >
            {e.text}
          </a>
        </li>
      ))}
    </ol>
  );

  return (
    <nav aria-label="On this page" className="font-landing-body">
      <details className="rounded-xl border border-site-line bg-site-card p-4 lg:hidden">
        <summary className="cursor-pointer text-sm font-semibold text-site-ink">On this page</summary>
        <div className="mt-3">{list}</div>
      </details>
      <div className="hidden lg:block">
        <b className="mb-3 block font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-faint">On this page</b>
        {list}
      </div>
    </nav>
  );
}
