import type { ComponentType } from "react";
import type { Rating, ResultTotals } from "@/capabilities/feedback";

/**
 * What the builder hands a dashboard preview: the draft's rating and resolved
 * display, and the totals the backend computed for its sample result.
 *
 * The learner dashboard lives in `domains/train`, which a capability may not
 * import. So the builder takes the preview as a component through this slot,
 * and the route (which may import a domain) passes
 * `domains/train/dashboard/RubricDashboardPreview` in. With no slot filled
 * the builder simply shows no dashboard tab.
 */
export interface RubricDashboardPreviewProps {
  rating: Rating;
  display: Record<string, unknown>;
  totals: ResultTotals | null;
}

export type RubricDashboardPreview = ComponentType<RubricDashboardPreviewProps>;
