import type { ReactNode } from "react";

type SectionTone = "ground" | "card" | "pale" | "navy";

const TONE: Record<SectionTone, string> = {
  ground: "bg-site-ground",
  card: "bg-site-card",
  pale: "bg-site-pale",
  navy: "bg-site-navy",
};

/** A full-width landing band with the shared shell and vertical rhythm. */
export function Section({ id, tone = "ground", label, children }: { id?: string; tone?: SectionTone; label?: string; children: ReactNode }) {
  return (
    <section id={id} aria-label={label} className={`scroll-mt-16 px-4 py-16 sm:px-6 sm:py-24 ${TONE[tone]}`}>
      <div className="mx-auto max-w-[1200px]">{children}</div>
    </section>
  );
}
