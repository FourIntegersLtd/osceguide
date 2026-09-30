"use client";

import type { ScreenMap, ScreenProps } from "@/surfaces/contract";
import { PartnerDashboard, PartnerReporting } from "@/domains/partner";
import { Team } from "@/domains/assess";

/**
 * The partner arm's screens.
 *
 * The growth endpoints key on a partner *name*, which is the organisation's
 * slug: `/api/v1/growth/partners/{partner}/funnel`. Taking it from the
 * workspace rather than from a separate setting keeps the two in step.
 *
 * `team` is Assess's screen on purpose. A partner's editors are memberships on
 * the same `/orgs/{slug}/memberships` routes as an institution's staff, so the
 * arm that needed a page of its own now needs a line in a map — and without it
 * a partner admin had no way to let anybody else into the catalogue.
 */

const partnerOf = ({ workspace }: ScreenProps) => workspace.orgSlug ?? "";

function PartnerOverviewScreen(props: ScreenProps) {
  return <PartnerDashboard partner={partnerOf(props)} />;
}

function PartnerReportingScreen(props: ScreenProps) {
  return <PartnerReporting partner={partnerOf(props)} />;
}

function PartnerTeamScreen(props: ScreenProps) {
  return <Team orgSlug={partnerOf(props)} />;
}

export const partnerScreens: ScreenMap = {
  dashboard: PartnerOverviewScreen,
  reporting: PartnerReportingScreen,
  team: PartnerTeamScreen,
};
