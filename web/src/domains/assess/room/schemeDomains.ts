/** A scheme's outline as domains with markable items; examiner notes never come through. */
import type { Scheme } from "@/domains/assess/room/api";
import { peerItem } from "@/domains/assess/room/peerMarks";

export interface SchemeDomain {
  id: string;
  title: string;
  instructions?: string;
  items: { key: string; label: string }[];
}

interface Block {
  block?: string;
  id?: string;
  title?: string;
  instructions?: string;
  competencies?: { id?: string; label?: string }[];
}

export function domainsOf(scheme: Scheme): SchemeDomain[] {
  const outline = (scheme.structure.outline as Block[] | undefined) ?? [];
  return outline
    .filter((b) => b.block === undefined || b.block === "domain")
    .map((b, i) => {
      const id = b.id ?? String(i);
      const comps = b.competencies ?? [];
      return {
        id,
        title: b.title ?? id,
        instructions: b.instructions,
        items: comps.length
          ? comps.map((c, n) => ({ key: peerItem(id, c.id ?? String(n)), label: c.label ?? "" }))
          : [{ key: id, label: b.title ?? id }],
      };
    });
}

/** The first domain with something left to mark, else the first. */
export function firstOpen(domains: SchemeDomain[], done: (key: string) => boolean): string | null {
  const left = domains.find((d) => d.items.some((i) => !done(i.key)));
  return (left ?? domains[0])?.id ?? null;
}

/** After `from` is finished: the next domain (wrapping) with something left, else stay closed. */
export function nextOpen(domains: SchemeDomain[], from: string, done: (key: string) => boolean): string | null {
  const start = domains.findIndex((d) => d.id === from);
  for (let step = 1; step <= domains.length; step++) {
    const d = domains[(start + step) % domains.length];
    if (d && d.items.some((i) => !done(i.key))) return d.id;
  }
  return null;
}
