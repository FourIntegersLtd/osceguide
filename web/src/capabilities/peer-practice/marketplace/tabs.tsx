"use client";

import type { B2CSegmentedTabItem } from "@/foundation/ui";

/** The three views of the marketplace, in the retiring screen's own order. */
export const MARKETPLACE_TABS: B2CSegmentedTabItem[] = [
  { id: "available", label: "All Sessions" },
  { id: "myPosts", label: "My Sessions" },
  { id: "upcoming", label: "Upcoming Sessions" },
];

export type MarketplaceTab = (typeof MARKETPLACE_TABS)[number]["id"];
