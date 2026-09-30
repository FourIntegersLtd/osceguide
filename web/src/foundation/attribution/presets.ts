import type {
  AttributionFilters,
  AttributionMode,
  AttributionQuery,
  RevenueTimeBucket,
} from "@/foundation/attribution/types";

/** The first day with any pilot data, so earlier dates are refused. */
export const EARLIEST_DATE = "2026-01-01";

export type RangePreset = "this_month" | "last_month" | "1m" | "3m" | "6m" | "custom";
export type ConcreteRangePreset = Exclude<RangePreset, "custom">;

export const RANGE_PRESET_ORDER: ConcreteRangePreset[] = [
  "this_month",
  "last_month",
  "1m",
  "3m",
  "6m",
];

export const RANGE_PRESET_LABELS: Record<RangePreset, string> = {
  this_month: "This month",
  last_month: "Last month",
  "1m": "Last 30 days",
  "3m": "Last 3 months",
  "6m": "Last 6 months",
  custom: "Custom",
};

const ROLLING_MONTHS: Partial<Record<ConcreteRangePreset, number>> = { "1m": 1, "3m": 3, "6m": 6 };

export function utcDateString(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function firstOfMonth(year: number, monthIndex: number): string {
  return utcDateString(new Date(Date.UTC(year, monthIndex, 1)));
}

function lastOfMonth(year: number, monthIndex: number): string {
  return utcDateString(new Date(Date.UTC(year, monthIndex + 1, 0)));
}

export function dateRangeForPreset(
  preset: ConcreteRangePreset,
  now: Date = new Date(),
): { fromDate: string; toDate: string } {
  const year = now.getUTCFullYear();
  const month = now.getUTCMonth();
  if (preset === "this_month") {
    return { fromDate: firstOfMonth(year, month), toDate: utcDateString(now) };
  }
  if (preset === "last_month") {
    return { fromDate: firstOfMonth(year, month - 1), toDate: lastOfMonth(year, month - 1) };
  }
  const from = new Date(now);
  from.setUTCMonth(from.getUTCMonth() - (ROLLING_MONTHS[preset] ?? 1));
  return { fromDate: utcDateString(from), toDate: utcDateString(now) };
}

export function detectRangePreset(
  fromDate: string,
  toDate: string,
  now: Date = new Date(),
): RangePreset {
  for (const preset of RANGE_PRESET_ORDER) {
    const range = dateRangeForPreset(preset, now);
    if (range.fromDate === fromDate && range.toDate === toDate) return preset;
  }
  return "custom";
}

/** Why a custom range is refused, or null when it is fine. */
export function validateCustomRange(
  fromDate: string,
  toDate: string,
  now: Date = new Date(),
): string | null {
  if (!fromDate || !toDate) return "Choose both a start and an end date.";
  if (fromDate > toDate) return "The start date must be on or before the end date.";
  if (toDate > utcDateString(now)) return "The end date can't be in the future.";
  if (fromDate < EARLIEST_DATE) {
    return `There's no data before ${EARLIEST_DATE}; the pilot started this year.`;
  }
  return null;
}

export function formatDisplayDate(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatDateRangeLabel(fromDate: string, toDate: string): string {
  return `${formatDisplayDate(fromDate)} – ${formatDisplayDate(toDate)}`;
}

/** The one line under the filter bar: `BMJ · SCA · 1 Sep 2026 – 30 Sep 2026`. */
export function formatActiveFilterSummary(
  filters: AttributionFilters,
  mode: AttributionMode,
): string {
  const parts: string[] = [];
  if (mode === "internal") parts.push(filters.partner.toUpperCase());
  parts.push(filters.exam ? filters.exam.toUpperCase() : "All exams");
  if (filters.utmCampaign) parts.push(filters.utmCampaign);
  parts.push(formatDateRangeLabel(filters.fromDate, filters.toDate));
  return parts.join(" · ");
}

export function formatGbpPence(pence: number): string {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(pence / 100);
}

export function formatChartPeriodLabel(period: string, bucket: RevenueTimeBucket): string {
  const parsed = new Date(`${period}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return period;
  if (bucket === "month") {
    return parsed.toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
  }
  return parsed.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

export function formatUtcDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return `${parsed.toLocaleString("en-GB", { timeZone: "UTC" })} UTC`;
}

/** Reads the filters out of the URL, defaulting to this month. A locked partner (a reporter) ignores `?partner=`. */
export function parseAttributionFilters(
  params: { get(name: string): string | null },
  lockedPartner: string | undefined,
  now: Date = new Date(),
): AttributionFilters {
  const thisMonth = dateRangeForPreset("this_month", now);
  const requestedPartner = params.get("partner");
  return {
    fromDate: params.get("from_date") ?? thisMonth.fromDate,
    toDate: params.get("to_date") ?? thisMonth.toDate,
    partner: lockedPartner ?? (requestedPartner === "bmj" ? requestedPartner : "bmj"),
    exam: params.get("exam") ?? "",
    utmCampaign: params.get("utm_campaign") ?? "",
  };
}

/** The query the growth routes take. The URL says `exam`; the API says `exam_code`. */
export function toAttributionQuery(filters: AttributionFilters): AttributionQuery {
  return {
    from_date: filters.fromDate,
    to_date: filters.toDate,
    exam_code: filters.exam || undefined,
    utm_campaign: filters.utmCampaign || undefined,
  };
}

/** True when any filter differs from the defaults, which is when "Reset filters" shows. */
export function hasActiveFilters(filters: AttributionFilters, now: Date = new Date()): boolean {
  const defaults = dateRangeForPreset("this_month", now);
  return (
    Boolean(filters.exam) ||
    Boolean(filters.utmCampaign) ||
    filters.fromDate !== defaults.fromDate ||
    filters.toDate !== defaults.toDate
  );
}
