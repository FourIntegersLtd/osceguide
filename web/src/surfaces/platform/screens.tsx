"use client";

import type { ScreenMap } from "@/surfaces/contract";
import { Organizations, PlatformOverview, Users } from "@/domains/platform";

export const platformScreens: ScreenMap = {
  dashboard: PlatformOverview,
  organizations: Organizations,
  users: Users,
};
