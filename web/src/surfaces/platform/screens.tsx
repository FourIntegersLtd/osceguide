"use client";

import type { ScreenMap } from "@/surfaces/contract";
import { BillingQueue, Ops, Organizations, PlatformAudit, PlatformOverview, PlatformTeam, ReferralPayouts, StationFlags, Users } from "@/domains/platform";

export const platformScreens: ScreenMap = {
  dashboard: PlatformOverview,
  organizations: Organizations,
  users: Users,
  team: PlatformTeam,
  billing: BillingQueue,
  audit: PlatformAudit,
  ops: Ops,
  stationFlags: StationFlags,
  referralPayouts: ReferralPayouts,
};
