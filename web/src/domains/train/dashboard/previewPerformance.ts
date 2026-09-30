import { readDisplay, type DomainTotal } from "@/capabilities/feedback/rubric";
import type { RubricDashboardPreviewProps } from "@/capabilities/authoring/rubrics/dashboardSlot";
import type { Performance } from "@/domains/train/api";

/**
 * A made-up `/me/performance` for a rubric that has no attempts yet.
 *
 * The rubric builder previews the learner dashboard a draft would give, and
 * the honest way to do that is to run the real `dashboardView` over a
 * performance read shaped like the API's. This builds one from the single
 * sample result the backend marked for the preview: each domain as its sample
 * total, and a three-point trend rising to the sample total so the chart has
 * a line to draw (the two earlier points are 70% and 85% of it). It is a
 * picture of the axes, labels and pass lines, not of anyone's progress.
 */

const EARLIER_SHARES = [0.7, 0.85, 1] as const;
const DAY_MS = 24 * 60 * 60 * 1000;

/** A domain's value as 0-100, the unit `DomainScore.score` is in. */
function domainScore(domain: DomainTotal, props: RubricDashboardPreviewProps): number {
  const display = readDisplay(props.display);
  if (display?.domain.aggregate === "ragCounts") {
    const counts = domain.counts ?? {};
    const all = Object.values(counts).reduce((total, count) => total + count, 0);
    const best = props.rating.scale?.[0];
    return all === 0 || best === undefined ? 0 : Math.round((100 * (counts[best] ?? 0)) / all);
  }
  const value = domain.value ?? 0;
  if (display?.domain.aggregate === "percentAchieved") return value;
  const max = display?.domain.max ?? props.rating.maximum ?? null;
  return max ? Math.round((100 * value) / max) : value;
}

export function previewPerformance(props: RubricDashboardPreviewProps, today: Date): Performance {
  const totals = props.totals;
  const domains = (totals?.domains ?? []).map((domain) => ({
    id: domain.id,
    label: domain.label,
    score: domainScore(domain, props),
    value: domain.value,
    counts: domain.counts ?? {},
  }));
  const share = totals?.fraction === null || totals?.fraction === undefined ? 0 : totals.fraction * 100;
  const trend =
    totals?.total === null || totals?.total === undefined
      ? []
      : EARLIER_SHARES.map((part, index) => ({
          date: new Date(today.getTime() - (EARLIER_SHARES.length - 1 - index) * 7 * DAY_MS).toISOString(),
          score: Math.round(share * part * 100) / 100,
          total: Math.round((totals.total ?? 0) * part * 100) / 100,
          passed: null,
        }));
  return {
    summary: { pass_rate: null, fail_rate: null, critical_rate: 0 },
    domains,
    trend,
    composition: [],
    mixed_versions: false,
    rubric_versions: 1,
    rating: props.rating,
    display: props.display,
    exam_code: null,
  };
}
