import type { AttributionMode } from "@/capabilities/attribution-dashboard/types";

export type AttributionTab =
  | "overview"
  | "revenue"
  | "performance"
  | "fee"
  | "activity"
  | "definitions"
  | "access";

export interface AttributionTabItem {
  id: AttributionTab;
  label: string;
  shortLabel: string;
}

const OVERVIEW: AttributionTabItem = { id: "overview", label: "Overview", shortLabel: "Overview" };
const REVENUE: AttributionTabItem = { id: "revenue", label: "Revenue", shortLabel: "Revenue" };
const ACTIVITY: AttributionTabItem = { id: "activity", label: "Recent activity", shortLabel: "Activity" };
const DEFINITIONS: AttributionTabItem = { id: "definitions", label: "How we count", shortLabel: "How we count" };
const ACCESS: AttributionTabItem = { id: "access", label: "Access", shortLabel: "Access" };
const PERFORMANCE: AttributionTabItem = { id: "performance", label: "Performance", shortLabel: "Performance" };
const FEE: AttributionTabItem = { id: "fee", label: "Your fee", shortLabel: "Your fee" };

/** Admin sees five tabs, a partner four, and a partner never gets Revenue. */
export function tabsForMode(mode: AttributionMode): AttributionTabItem[] {
  return mode === "internal"
    ? [OVERVIEW, REVENUE, ACTIVITY, DEFINITIONS, ACCESS]
    : [OVERVIEW, PERFORMANCE, FEE, DEFINITIONS];
}

export const DEFAULT_ATTRIBUTION_TAB: AttributionTab = "overview";

/** A `?tab=` value that is not a tab for this mode falls back to Overview. */
export function parseAttributionTab(value: string | null, mode: AttributionMode): AttributionTab {
  const match = tabsForMode(mode).find((tab) => tab.id === value);
  return match ? match.id : DEFAULT_ATTRIBUTION_TAB;
}

/** What the top filter bar shows on each tab. */
export type FilterScope = "full" | "partner-only" | "hidden";

export function filterScope(tab: AttributionTab, mode: AttributionMode): FilterScope {
  if (tab === "access") return mode === "internal" ? "partner-only" : "hidden";
  return "full";
}
