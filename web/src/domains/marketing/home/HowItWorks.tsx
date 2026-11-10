import type { CSSProperties } from "react";
import { Eyebrow, SiteContainer } from "@/foundation/ui";
import { HOW_IT_WORKS } from "@/domains/marketing/landingCopy";
import { CasesVignette, ConsultVignette, MarksVignette } from "@/domains/marketing/home/HowItWorksVignettes";
import {
  HOW_CURVE, HOW_GRID_YS, HOW_LEGEND, HOW_NODES, HOW_NODE_RADIUS, HOW_PANEL, HOW_STEM, HOW_STEM_TOP, HOW_STEP_GAP,
} from "@/domains/marketing/home/howItWorksData";

/** Each step: its node on the curve, its vignette and its copy. */
const STEPS = [
  { ...HOW_NODES[0], Vignette: CasesVignette, title: HOW_IT_WORKS.items[0].title },
  { ...HOW_NODES[1], Vignette: ConsultVignette, title: HOW_IT_WORKS.items[1].title },
  { ...HOW_NODES[2], Vignette: MarksVignette, title: HOW_IT_WORKS.items[2].title },
];
const NODE = "inline-flex items-center justify-center rounded-full bg-site-brand font-landing-mono font-semibold text-site-on-brand";
const pct = (x: number) => `${(x / HOW_PANEL.width) * 100}%`;

/** A rising curve with three numbered steps on it from xl up (a stacked spine below, where the fixed-width callouts would not fit). Server-rendered; the `<ol>` carries the content, the rest is decoration. */
export function HowItWorks() {
  return (
    <section id="how" aria-labelledby="how-title" className="scroll-mt-16 bg-site-card pb-12 pt-16 md:pt-[360px] lg:pb-24">
      <SiteContainer>
        <div className="max-w-[680px]">
          <Eyebrow>{HOW_IT_WORKS.eyebrow}</Eyebrow>
          <h2 id="how-title" className="mt-3 font-landing-heading text-[32px] font-semibold leading-[1.1] tracking-tight text-site-ink lg:text-[44px] lg:leading-[1.08]">{HOW_IT_WORKS.title}</h2>
        </div>
        <div style={{ "--h": `${HOW_PANEL.height}px` } as CSSProperties} className="relative mt-8 xl:mt-14 xl:h-[var(--h)] xl:overflow-hidden xl:rounded-[28px] xl:border xl:border-site-line xl:bg-site-ground/50">
          <span aria-hidden="true" className="absolute bottom-10 left-[19px] top-10 w-0.5 bg-gradient-to-b from-site-on-deep to-site-brand xl:hidden" />
          <svg aria-hidden="true" viewBox={`0 0 ${HOW_PANEL.width} ${HOW_PANEL.height}`} preserveAspectRatio="none" className="absolute inset-0 hidden h-full w-full xl:block" fill="none">
            <defs>
              <linearGradient id="how-area" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="var(--site-brand)" stopOpacity="0.16" />
                <stop offset="1" stopColor="var(--site-brand)" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="how-line" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stopColor="var(--site-on-deep)" />
                <stop offset="1" stopColor="var(--site-brand)" />
              </linearGradient>
            </defs>
            {HOW_GRID_YS.map((y) => (
              <line key={y} x1="0" x2={HOW_PANEL.width} y1={y} y2={y} stroke="var(--site-line)" strokeWidth="1" />
            ))}
            <path d={`${HOW_CURVE} L ${HOW_PANEL.width} ${HOW_PANEL.height} L 0 ${HOW_PANEL.height} Z`} fill="url(#how-area)" />
            <path d={HOW_CURVE} stroke="url(#how-line)" strokeWidth="3" strokeLinecap="round" />
          </svg>
          <span aria-hidden="true" className="absolute left-6 top-6 hidden items-center gap-2 rounded-full border border-site-line bg-site-card px-3 py-1.5 font-landing-mono text-xs font-medium text-site-body xl:inline-flex">
            <i className="h-2 w-2 rounded-full bg-site-brand" />
            {HOW_LEGEND}
          </span>
          <ol className="relative flex flex-col gap-8 xl:absolute xl:inset-0 xl:block">
            {STEPS.map(({ n, x, y, w, Vignette, title }) => {
              const place = { "--x": pct(x - w / 2), "--w": `${w}px`, "--b": `${HOW_PANEL.height - (y - HOW_STEP_GAP)}px` } as CSSProperties;
              return (
                <li key={n} style={place} className="relative pl-14 xl:absolute xl:bottom-[var(--b)] xl:left-[var(--x)] xl:w-[var(--w)] xl:pl-0">
                  <span aria-hidden="true" className={`${NODE} absolute left-0 top-0 h-10 w-10 text-[13px] ring-[6px] ring-site-brand/15 xl:hidden`}>{n}</span>
                  <h3 className="pt-2 text-lg font-semibold leading-[1.3] text-site-ink xl:pt-0 xl:text-[19px]">{title}</h3>
                  <div className="mt-3">
                    <Vignette />
                  </div>
                </li>
              );
            })}
          </ol>
          <div aria-hidden="true" className="hidden xl:block">
            {STEPS.map(({ n, x, y }) => (
              <div key={n}>
                <span className="absolute w-0.5 -translate-x-1/2 bg-site-brand/50" style={{ left: pct(x), top: y - HOW_STEM_TOP, height: HOW_STEM }} />
                <span className={`${NODE} absolute -translate-x-1/2 text-sm ring-8 ring-site-brand/15`} style={{ left: pct(x), top: y - HOW_NODE_RADIUS, width: HOW_NODE_RADIUS * 2, height: HOW_NODE_RADIUS * 2 }}>{n}</span>
              </div>
            ))}
          </div>
        </div>
      </SiteContainer>
    </section>
  );
}
