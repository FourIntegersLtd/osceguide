"use client";

import { boardAlert, boardPad } from "@/foundation/ui/boardKit";
import { formatMoney } from "@/foundation/format";
import { useState, type ReactNode } from "react";
import { b2bTokens, cn } from "@/foundation/ui";
import { CustomDateRangeModal } from "@/capabilities/attribution-dashboard/CustomDateRangeModal";
import {
  RANGE_PRESET_LABELS,
  RANGE_PRESET_ORDER,
  detectRangePreset,
  formatActiveFilterSummary,
  formatDateRangeLabel,
  type ConcreteRangePreset,
} from "@/capabilities/attribution-dashboard/presets";
import {
  PILOT_EXAMS,
  type AttributionFilters,
} from "@/capabilities/attribution-dashboard/types";

/*
 * The partner screens' pieces, drawn the way the Partner board draws them
 * (docs/institution-overhaul/boards/Partner.dc.html), from the assess tokens. The data, the words
 * and the filters are the attribution-dashboard capability's; only the look is the partner arm's,
 * so the staff growth screens that share that capability are untouched.
 */

const select =
  "box-border min-h-11 w-full min-w-0 rounded-control border border-osce-border bg-osce-surface px-3 text-assess-desc text-osce-ink-900";

/** Eyebrow, title and lead, as every board screen opens. */
export function PartnerHeader({ title, lead }: { title: string; lead: string }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className={b2bTokens.assessEyebrow}>Partner</div>
        <h1 className={b2bTokens.assessTitle}>{title}</h1>
        <p className={b2bTokens.assessDesc}>{lead}</p>
      </div>
    </div>
  );
}

/** The board's `.card.pad`: a titled card whose children sit 14px apart. */
export function PartnerCard({
  eyebrow,
  title,
  lead,
  label,
  children,
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
  label?: string;
  children: ReactNode;
}) {
  return (
    <section aria-label={label ?? title} className={cn(boardPad, "overflow-hidden")}>
      {eyebrow ? <div className={b2bTokens.assessEyebrow}>{eyebrow}</div> : null}
      <h2 className="text-base font-semibold !leading-[normal] text-osce-ink-900">{title}</h2>
      {lead ? <div className={b2bTokens.assessMeta}>{lead}</div> : null}
      {children}
    </section>
  );
}

/** The board's `.g3`: three tiles a row, one on a phone. */
export function Tiles({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-3 min-[901px]:grid-cols-3">{children}</div>;
}

export function Tile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className={cn(b2bTokens.assessCard, "p-4")}>
      <div className={b2bTokens.assessEyebrow}>{label}</div>
      <div className="text-assess-num font-semibold text-osce-ink-900">{value}</div>
      <div className={b2bTokens.assessMeta}>{note}</div>
    </div>
  );
}

/** The board's `.al.info`: a bold line, then the words. */
function InfoNote({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div role="note" className={boardAlert("info")}>
      <b className="block font-semibold">{title}</b> {children}
    </div>
  );
}

/** The server's fee disclaimer and the per-visit rate it is using; a plain "guide only" note until the summary has loaded. */
export function FeeNote({ fee }: { fee: { billing_disclaimer: string; cost_per_click_pence: number } | null | undefined }) {
  if (!fee) {
    return (
      <InfoNote title="Fee estimates are a guide only">
        The fee shown here is an estimate from our arrival counts. You invoice from your own click records; nothing on this page is a bill.
      </InfoNote>
    );
  }
  return (
    <InfoNote title="Estimated fee (guide only)">
      {fee.billing_disclaimer} We&apos;re using <strong>{formatMoney(fee.cost_per_click_pence)}</strong> per link visit.
    </InfoNote>
  );
}

/** Date range and exam as two selects, the summary, Reset filters and when the numbers arrived. */
export function FilterCard({
  filters,
  onChange,
  onPresetSelect,
  onReset,
  updatedAt,
}: {
  filters: AttributionFilters;
  onChange: (next: Partial<AttributionFilters>) => void;
  onPresetSelect: (preset: ConcreteRangePreset) => void;
  onReset: () => void;
  updatedAt: Date | null;
}) {
  const [customOpen, setCustomOpen] = useState(false);
  const preset = detectRangePreset(filters.fromDate, filters.toDate);
  return (
    <>
      <div className={boardPad}>
        <div className="flex flex-wrap items-center gap-2">
          <div className="max-w-[180px] flex-1 basis-[140px]">
            <select
              aria-label="Date range"
              className={select}
              value={preset}
              onChange={(event) => {
                if (event.target.value === "custom") setCustomOpen(true);
                else onPresetSelect(event.target.value as ConcreteRangePreset);
              }}
            >
              {RANGE_PRESET_ORDER.map((value) => (
                <option key={value} value={value}>
                  {RANGE_PRESET_LABELS[value]}
                </option>
              ))}
              <option value="custom">{preset === "custom" ? formatDateRangeLabel(filters.fromDate, filters.toDate) : "Custom"}</option>
            </select>
          </div>
          <div className="max-w-[140px] flex-1 basis-[110px]">
            <select aria-label="Exam" className={select} value={filters.exam} onChange={(event) => onChange({ exam: event.target.value })}>
              <option value="">All exams</option>
              {PILOT_EXAMS.map((exam) => (
                <option key={exam} value={exam}>
                  {exam.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          <span className={cn(b2bTokens.assessMeta, "min-w-0 flex-1")}>{formatActiveFilterSummary(filters, "partner")} · UK calendar days</span>
          <button type="button" onClick={onReset} className="text-assess-label text-osce-accent hover:text-osce-accent-hover">
            Reset filters
          </button>
          {updatedAt ? (
            <span className={b2bTokens.assessMeta}>Updated {updatedAt.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</span>
          ) : null}
        </div>
      </div>
      <CustomDateRangeModal
        open={customOpen}
        fromDate={filters.fromDate}
        toDate={filters.toDate}
        onClose={() => setCustomOpen(false)}
        onApply={(range) => onChange(range)}
      />
    </>
  );
}

/** Bars from a series; each bar says its own period and value to a pointer and to a screen reader. */
export function Bars({ points, summary }: { points: { label: string; value: number; text: string }[]; summary: string }) {
  const max = Math.max(1, ...points.map((point) => point.value));
  return (
    <div role="img" aria-label={summary} className="flex h-[140px] items-end gap-1.5">
      {points.map((point) => (
        <div
          key={point.label}
          title={`${point.label}: ${point.text}`}
          className="flex-1 rounded-t bg-osce-accent opacity-80"
          style={{ height: `${Math.max(2, Math.round((point.value / max) * 100))}%` }}
        />
      ))}
    </div>
  );
}

/** A bordered list of rows, the board's `.card` of `.row`s. */
export function RowList({ children }: { children: ReactNode }) {
  return <div className={cn(b2bTokens.assessCard, "overflow-hidden")}>{children}</div>;
}

export function Row({ children, first }: { children: ReactNode; first?: boolean }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-4 px-5 py-3.5 text-assess-label text-osce-ink-900", !first && "border-t border-osce-border-light")}>
      {children}
    </div>
  );
}

/** One rule of "How we count": a bold term, a Plain English chip, then the sentence. */
export function Definition({ term, detail, first }: { term: string; detail: string; first?: boolean }) {
  return (
    <Row first={first}>
      <span className="min-w-0 flex-1">
        <b className="font-semibold">{term}</b> <span className={b2bTokens.assessChipNeutral}>Plain English</span>
        <div className={b2bTokens.assessMeta}>{detail}</div>
      </span>
    </Row>
  );
}
