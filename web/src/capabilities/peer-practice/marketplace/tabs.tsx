"use client";

import { HiOutlineCalendarDays, HiOutlineClock, HiOutlineUser } from "react-icons/hi2";
import type { B2CSegmentedTabItem } from "@/foundation/ui";

export type MarketplaceTab = "available" | "myPosts" | "upcoming";

/** The three views of the marketplace, in the retiring screen's own order and with its icons. */
export const MARKETPLACE_TABS: B2CSegmentedTabItem<MarketplaceTab>[] = [
  {
    id: "available",
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlineCalendarDays className="h-4 w-4" aria-hidden />
        All sessions
      </span>
    ),
  },
  {
    id: "myPosts",
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlineUser className="h-4 w-4" aria-hidden />
        My sessions
      </span>
    ),
  },
  {
    id: "upcoming",
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlineClock className="h-4 w-4" aria-hidden />
        Upcoming sessions
      </span>
    ),
  },
];
