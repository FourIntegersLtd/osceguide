import { AthenaAvatar } from "@/foundation/ui";
import { HOW_CASES, HOW_CONSULT, HOW_DECK, HOW_MARKS, VIGNETTE_H } from "@/domains/marketing/home/howItWorksData";

const MONO = "font-landing-mono font-medium";
const LABEL = `${MONO} text-[11px] uppercase tracking-[0.1em] text-site-muted`;
const CHIP = `${MONO} rounded-full bg-site-pale px-2 py-[3px] text-[11px] text-site-brand`;
const CARD = "rounded-[14px] border bg-site-card";
const BUBBLE = "absolute px-4 py-3 text-[13px] leading-[1.45] shadow-lg";
const HEIGHT = { height: VIGNETTE_H };

/** Step 1: how many cases, and a fanned deck. Illustrative, so aria-hidden. */
export function CasesVignette() {
  return (
    <div aria-hidden="true" className="relative" style={HEIGHT}>
      <div className="absolute left-0 top-0 flex items-center gap-1.5">
        <span className={`${LABEL} mr-1.5`}>{HOW_CASES.label}</span>
        {HOW_CASES.counts.map((count) => (
          <span
            key={count}
            className={`inline-flex h-9 w-10 items-center justify-center rounded-[10px] text-sm font-semibold ${
              count === HOW_CASES.selected ? "-translate-y-1 bg-site-brand text-site-on-brand shadow-lg" : "border border-site-rule bg-site-card text-site-body"
            }`}
          >
            {count}
          </span>
        ))}
      </div>
      <div className={`${CARD} absolute left-[18px] top-[70px] h-[120px] w-[min(250px,calc(100%-28px))] -rotate-6 border-site-line shadow-lg`} />
      <div className={`${CARD} absolute left-7 top-[62px] h-[120px] w-[min(250px,calc(100%-28px))] -rotate-2 border-site-line shadow-lg`} />
      <div className={`${CARD} absolute left-[38px] top-[54px] flex h-[124px] w-[min(250px,calc(100%-38px))] flex-col gap-2.5 border-site-rule px-4 py-3.5 shadow-xl`}>
        <div className="flex items-center justify-between">
          <span className={CHIP}>{HOW_DECK.chip}</span>
          <span className={`${MONO} text-[11px] text-site-muted`}>{HOW_DECK.progress}</span>
        </div>
        <span className="h-[9px] w-[70%] rounded bg-site-ink/85" />
        <span className="h-[7px] w-[52%] rounded bg-site-pale" />
        <span className="h-[7px] w-[60%] rounded bg-site-pale" />
      </div>
    </div>
  );
}

/** Step 2: a few seconds of a consultation. Illustrative, so aria-hidden. */
export function ConsultVignette() {
  return (
    <div aria-hidden="true" className="relative" style={HEIGHT}>
      <span className={`${MONO} absolute right-0 top-0 inline-flex items-center gap-1.5 rounded-full border border-site-line bg-site-card px-2.5 py-[5px] text-xs text-site-ink`}>
        <i className="h-1.5 w-1.5 rounded-full bg-site-brand" />
        {HOW_CONSULT.clock}
      </span>
      <div className={`${BUBBLE} left-0 top-[34px] max-w-[92%] sm:max-w-[82%] rounded-[18px] rounded-bl-[4px] border border-site-line bg-site-card text-site-body`}>{HOW_CONSULT.patient}</div>
      <div className="absolute left-2 top-[124px] sm:top-[112px] flex h-7 items-center gap-[3px]">
        {HOW_CONSULT.wave.map(([height, opacity], i) => (
          <i key={i} className="w-[3px] rounded-sm bg-site-brand" style={{ height, opacity }} />
        ))}
      </div>
      <div className={`${BUBBLE} right-0 top-[156px] max-w-[90%] sm:top-[150px] sm:max-w-[78%] rounded-[18px] rounded-br-[4px] bg-site-deep text-white`}>{HOW_CONSULT.doctor}</div>
    </div>
  );
}

/** Step 3: a marked case and the tutor's first line. Illustrative, so aria-hidden. */
export function MarksVignette() {
  return (
    <div aria-hidden="true" className="rounded-[20px] border border-site-line bg-site-card p-4 shadow-xl">
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className={LABEL}>{HOW_MARKS.title}</span>
          <span className={CHIP}>{HOW_MARKS.chip}</span>
        </div>
        {HOW_MARKS.domains.map((d) => (
          <div key={d.label}>
            <div className="flex justify-between text-[13px] font-medium text-site-ink">
              <span>{d.label}</span>
              <span className="font-normal text-site-muted">{d.level}</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-[3px] bg-site-pale">
              <span className="block h-full rounded-[3px] bg-gradient-to-r from-site-deep to-site-brand" style={{ width: `${d.percent}%` }} />
            </div>
          </div>
        ))}
        <div className="flex items-center gap-2.5 rounded-xl border border-site-line bg-site-card px-3 py-2.5">
          <AthenaAvatar className="h-7 w-7" />
          <span className="text-[13px] leading-[1.4] text-site-body">{HOW_MARKS.athena}</span>
        </div>
      </div>
    </div>
  );
}
