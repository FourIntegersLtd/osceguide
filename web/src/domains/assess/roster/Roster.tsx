"use client";

import { useRef, useState } from "react";
import { AsyncBoundary, Button, B2CHero, B2CPageHeader, TextLink } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { TabStrip } from "@/domains/assess/team/chrome";
import { listAllTrainees, listCohorts, listTraineeGroups } from "@/domains/assess/roster/api";
import { TraineesPanel } from "@/domains/assess/roster/TraineesPanel";
import { AddTraineePanel } from "@/domains/assess/roster/AddTraineePanel";
import { GroupsPanel } from "@/domains/assess/roster/GroupsPanel";
import { AccessPanel } from "@/domains/assess/roster/AccessPanel";
import type { Trainee } from "@/domains/assess/api";
import { loadRoster, rosterTabs, sectionSubtitle, type RosterData } from "@/domains/assess/roster/support";

type Section = "trainees" | "add" | "groups" | "access";
type Part = keyof RosterData;

/**
 * The roster: who the organisation examines.
 *
 * Separate from Team, which is the staff who run the examination. The three
 * lists are loaded once for the whole screen rather than per tab — the old
 * client had each of these as its own route and refetched the roster on every
 * visit — and every write reloads all three, because adding a trainee changes
 * a group's count and granting access changes nothing else on the page.
 */
export function Trainees({ orgSlug }: { orgSlug: string }) {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const [section, setSection] = useState<Section>("trainees");
  const canManage = can(session, "manage_team");

  // Lists a write has changed; the rest are served from the last load (see `loadRoster`).
  const cache = useRef<{ slug?: string; data?: RosterData }>({});
  const stale = useRef<Set<Part>>(new Set(["trainees", "cohorts", "groups"]));
  const state = useAsync(
    async (signal) => {
      const parts = new Set(stale.current);
      stale.current = new Set();
      try {
        return await loadRoster(cache.current, orgSlug, parts, {
          trainees: () => listAllTrainees(orgSlug, signal),
          cohorts: async () => (await listCohorts(orgSlug, signal)).items,
          groups: async () => (await listTraineeGroups(orgSlug, signal)).items,
        });
      } catch (cause) {
        // Nothing was cached, so the next attempt must fetch what this one meant to.
        parts.forEach((part) => stale.current.add(part));
        throw cause;
      }
    },
    [orgSlug],
  );
  const reloadAfter = (...parts: Part[]) => () => {
    parts.forEach((part) => stale.current.add(part));
    state.reload();
  };

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(data) => (
          <>
            <B2CPageHeader
              title="People"
              subtitle={sectionSubtitle(section, {
                trainees: data.trainees.length,
                groups: data.groups.length,
              })}
              action={
                canManage && section === "trainees" ? (
                  <Button themeType="b2b" variant="commit" onClick={() => setSection("add")}>
                    Add people
                  </Button>
                ) : null
              }
            />

            {section === "trainees" && data.trainees.length > 0 ? (
              <B2CHero title={rosterHeadline(data.trainees)}>
                {rosterDetail(data.trainees)}
              </B2CHero>
            ) : null}

            <TabStrip
              tabs={rosterTabs(canManage).map((tab) =>
                tab.key === "trainees" ? { ...tab, count: data.trainees.length } : tab,
              )}
              active={section} onSelect={setSection}
              label="Roster sections"
            />

            {section === "trainees" ? (
              <TraineesPanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                canManage={canManage}
                onChanged={reloadAfter("trainees", "groups")}
              />
            ) : null}

            {section === "add" ? (
              <AddTraineePanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                canManage={canManage}
                onAdded={reloadAfter("trainees", "groups")}
              />
            ) : null}

            {section === "groups" ? (
              <GroupsPanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                groups={data.groups}
                trainees={data.trainees}
                canManage={canManage}
                onChanged={reloadAfter("groups", "cohorts")}
              />
            ) : null}

            {section === "access" && canManage ? (
              <AccessPanel orgSlug={orgSlug} trainees={data.trainees} canManage />
            ) : null}
          </>
        )}
      </AsyncBoundary>

      {canManage ? (
        <p className="text-osce-caption text-b2b-mid">
          Looking for supervisors and admins?{" "}
          <TextLink themeType="b2b" href={hrefFor("/team")}>
            Go to the team
          </TextLink>
          .
        </p>
      ) : null}
    </div>
  );
}

function programmeCount(trainees: Trainee[]): number {
  return new Set(trainees.flatMap((trainee) => trainee.programme_names ?? [])).size;
}

/** "N trainees across M programmes", counting only programmes someone is rostered on. */
function rosterHeadline(trainees: Trainee[]): string {
  const people = `${trainees.length} ${trainees.length === 1 ? "trainee" : "trainees"}`;
  const count = programmeCount(trainees);
  return `${people} across ${count} ${count === 1 ? "programme" : "programmes"}`;
}

function rosterDetail(trainees: Trainee[]): string {
  const sat = trainees.reduce((total, trainee) => total + trainee.stations_sat, 0);
  return `${sat} ${sat === 1 ? "station" : "stations"} sat so far.`;
}
