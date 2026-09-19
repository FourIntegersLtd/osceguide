"use client";

import { HiOutlineCalendarDays, HiOutlineClock, HiOutlineUser } from "react-icons/hi2";

/** The three views of the marketplace, in the retiring screen's own order. */
export const MARKETPLACE_TABS = [
  {
    id: "available" as const,
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlineCalendarDays className="h-4 w-4" aria-hidden />
        All Sessions
      </span>
    ),
  },
  {
    id: "myPosts" as const,
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlineUser className="h-4 w-4" aria-hidden />
        My Sessions
      </span>
    ),
  },
  {
    id: "upcoming" as const,
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlineClock className="h-4 w-4" aria-hidden />
        Upcoming Sessions
      </span>
    ),
  },
];

export type MarketplaceTab = (typeof MARKETPLACE_TABS)[number]["id"];
