"use client";

import type { ScreenMap, ScreenProps } from "@/surfaces/contract";
import { PartnerDashboard, PartnerReporting } from "@/domains/partner";

/**
 * The partner arm's screens.
 *
 * The growth endpoints key on a partner *name*, which is the organisation's
 * slug: `/api/v1/growth/partners/{partner}/funnel`. Taking it from the
 * workspace rather than from a separate setting keeps the two in step.
 */

const partnerOf = ({ workspace }: ScreenProps) => workspace.orgSlug ?? "";

function PartnerOverviewScreen(props: ScreenProps) {
  return <PartnerDashboard partner={partnerOf(props)} />;
}

function PartnerReportingScreen(props: ScreenProps) {
  return <PartnerReporting partner={partnerOf(props)} />;
}

export const partnerScreens: ScreenMap = {
  dashboard: PartnerOverviewScreen,
  reporting: PartnerReportingScreen,
};
