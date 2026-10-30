import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import { Eyebrow, IconTile, SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

/** The bordered card every landing band sets its content in. */
export const SITE_CARD = "rounded-2xl border border-site-line bg-site-card p-6";
export const CARD_TITLE = "text-balance break-words font-landing-heading text-xl font-bold leading-snug text-site-ink";

type Tone = "ground" | "card" | "pale";

/** `label` sits under the icon; `aside` sits opposite it. */
export type CardItem = { Icon?: IconType; label?: string; aside?: ReactNode; title: string; body?: string };

/** A landing band with a centred heading and optional sub line; the content sits 48px below. */
export function TitledSection({ id, tone = "ground", title, sub, children }: { id?: string; tone?: Tone; title: ReactNode; sub?: string; children?: ReactNode }) {
  return (
    <Section id={id} tone={tone}>
      <SectionHead title={title} sub={sub} />
      {children && <div className="mt-12 space-y-12 sm:space-y-16">{children}</div>}
    </Section>
  );
}

/** Cards in a grid: an icon tile when the card has an icon, a small label under it when it has one. */
export function CardGrid({ items, className = "md:grid-cols-3" }: { items: readonly CardItem[]; className?: string }) {
  return (
    <div className={`grid gap-5 ${className}`}>
      {items.map(({ Icon, label, aside, title, body }) => (
        <div key={title} className={`flex h-full min-w-0 flex-col ${SITE_CARD}`}>
          {(Icon || aside) && (
            <div className="flex items-center justify-between gap-3">
              {Icon && <IconTile><Icon /></IconTile>}
              {aside}
            </div>
          )}
          {label && <b className="mt-4 block font-landing-mono text-[11px] font-medium tracking-[0.13em] text-site-brand">{label}</b>}
          <h3 className={`${Icon || label ? "mt-4" : ""} ${CARD_TITLE}`}>{title}</h3>
          {body && <p className="mt-2 leading-relaxed text-site-body">{body}</p>}
        </div>
      ))}
    </div>
  );
}

/** One line per entry with a brand dot. */
export function BulletList({ items }: { items: readonly string[] }) {
  return (
    <ul className="space-y-3">
      {items.map((entry) => (
        <li key={entry} className="flex items-start gap-3 text-site-ink">
          <span aria-hidden="true" className="mt-2 h-2 w-2 shrink-0 rounded-full bg-site-brand" />
          {entry}
        </li>
      ))}
    </ul>
  );
}

/** Bordered bullet lists side by side. */
export function Checklist({ columns }: { columns: readonly (readonly string[])[] }) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      {columns.map((column, i) => (
        <div key={i} className={SITE_CARD}>
          <BulletList items={column} />
        </div>
      ))}
    </div>
  );
}

/** The first screen's headline, lead and funnel links; `children` is whatever shows under them. */
export function HeroIntro({ title, lead, ctas, titleClass = "text-[clamp(1.75rem,6vw,3.5rem)]", children }: { title: ReactNode; lead: string; ctas: ReactNode; titleClass?: string; children?: ReactNode }) {
  return (
    <>
      <h1 className={`mx-auto mt-6 max-w-4xl text-balance font-landing-heading font-bold leading-[1.1] tracking-tight text-site-ink ${titleClass}`}>{title}</h1>
      <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-site-body">{lead}</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">{ctas}</div>
      {children}
    </>
  );
}

/** A long note from the team in one card: eyebrow, paragraphs, signature. */
export function LetterCard({ eyebrow, icon, title, paragraphs, signoff }: { eyebrow: string; icon?: ReactNode; title?: string; paragraphs: readonly string[]; signoff: ReactNode }) {
  return (
    <article className="mx-auto max-w-3xl rounded-3xl border border-site-line bg-site-card p-6 sm:p-10">
      <div className="flex items-center gap-3">
        {icon && <IconTile>{icon}</IconTile>}
        <Eyebrow>{eyebrow}</Eyebrow>
      </div>
      {title && <h2 className="mt-4 text-balance font-landing-heading text-3xl font-bold leading-tight text-site-ink">{title}</h2>}
      <div className="mt-6 space-y-4 text-[17px] leading-[1.7] text-site-body">
        {paragraphs.map((text) => (
          <p key={text}>{text}</p>
        ))}
      </div>
      <p className="mt-7 flex flex-wrap items-baseline gap-x-2 border-t border-site-line pt-6">{signoff}</p>
    </article>
  );
}
