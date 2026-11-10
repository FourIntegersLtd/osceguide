import type { ReactNode } from "react";
import { SiteContainer } from "@/foundation/ui";

type SectionTone = "ground" | "card" | "pale" | "navy";

const TONE: Record<SectionTone, string> = {
  ground: "bg-site-ground",
  card: "bg-site-card",
  pale: "bg-site-pale",
  navy: "bg-site-navy",
};

/** A full-width landing band with the shared shell and vertical rhythm; `pad` replaces the default vertical padding where a band sits tighter against its neighbour. */
export function Section({ id, tone = "ground", label, pad = "py-20 sm:py-32", children }: { id?: string; tone?: SectionTone; label?: string; pad?: string; children: ReactNode }) {
  return (
    <section id={id} aria-label={label} className={`scroll-mt-16 ${TONE[tone]}`}>
      <SiteContainer className={pad}>{children}</SiteContainer>
    </section>
  );
}
