import type { ReactNode } from "react";

type Tone = "ok" | "dev" | "pass";

function Pill({ tone, children }: { tone: Tone; children: ReactNode }) {
  // Amber is reserved for the "developing" band.
  const cls = tone === "dev" ? "bg-site-amber-bg text-site-amber" : "bg-site-pale text-site-brand";
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>{children}</span>;
}

export { Pill };

function Domain({ name, band, tone, pct }: { name: string; band: string; tone: Tone; pct: number }) {
  return (
    <div className="rounded-xl border border-site-line p-4">
      <div className="flex items-center justify-between gap-2 text-sm font-semibold text-site-ink">
        {name}
        <Pill tone={tone}>{band}</Pill>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-site-line">
        <i className={`block h-full rounded-full ${tone === "dev" ? "bg-site-amber" : "bg-site-brand"}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function Moment({ time, quote, note, missed = false }: { time: string; quote: string; note: string; missed?: boolean }) {
  return (
    <div className={`flex gap-3 rounded-lg p-3 text-left ${missed ? "bg-site-amber-bg" : "bg-site-pale"}`}>
      <b className="font-landing-mono text-sm text-site-ink">{time}</b>
      <span className="text-sm text-site-body">
        <q>{quote}</q>
        <small className={`mt-0.5 block ${missed ? "text-site-amber" : "text-site-muted"}`}>{note}</small>
      </span>
    </div>
  );
}

/** A sample feedback report: an illustration of the product, not a real candidate's result. */
export function ReportShowcase() {
  return (
    <div
      role="img"
      aria-label="Example feedback report: overall pass, three domains with scores, and the transcript moments where marks were decided"
      className="mx-auto mt-12 max-w-3xl"
    >
      <div aria-hidden="true" className="rounded-2xl border border-site-line bg-site-card p-5 text-left shadow-sm sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="font-landing-heading text-lg font-bold text-site-ink">Station 7 · Morning headaches</div>
            <div className="font-landing-mono text-[11px] uppercase tracking-[0.1em] text-site-faint">SCA · TELEPHONE · 11:48</div>
          </div>
          <span className="flex items-center gap-3">
            <span className="site-pulse font-landing-mono text-[11px] text-site-faint">MARKED JUST NOW</span>
            <Pill tone="pass">Clear pass</Pill>
          </span>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <Domain name="Data gathering" band="Competent" tone="ok" pct={75} />
          <Domain name="Clinical management" band="Developing" tone="dev" pct={58} />
          <Domain name="Relating to others" band="Competent" tone="ok" pct={92} />
        </div>
        <h3 className="mt-6 text-sm font-semibold text-site-ink">Where marks were decided</h3>
        <div className="mt-3 space-y-2">
          <Moment time="03:42" quote="Is there anything in particular you've been worried about?" note="Explored her concern. Mark earned." />
          <Moment time="01:20" quote="Okay. And how are you sleeping?" note="Moved past blurred vision. Mark missed." missed />
          <Moment time="11:20" quote="If the headache becomes sudden and severe, call 999." note="Safety-net given. Mark earned." />
        </div>
      </div>
    </div>
  );
}
