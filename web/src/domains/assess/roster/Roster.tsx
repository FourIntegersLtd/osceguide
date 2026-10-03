"use client";

import { useState } from "react";
import { AsyncBoundary, Button, B2CHero, B2CPageHeader, TextLink } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { TabStrip, type Tab } from "@/domains/assess/team/chrome";
import { listAllTrainees, listCohorts, listTraineeGroups } from "@/domains/assess/roster/api";
import { TraineesPanel } from "@/domains/assess/roster/TraineesPanel";
import { AddTraineePanel } from "@/domains/assess/roster/AddTraineePanel";
import { GroupsPanel } from "@/domains/assess/roster/GroupsPanel";
import { AccessPanel } from "@/domains/assess/roster/AccessPanel";
import type { Trainee } from "@/domains/assess/api";
import { sectionSubtitle } from "@/domains/assess/roster/support";

type Section = "trainees" | "add" | "groups" | "access";

const TABS: readonly Tab<Section>[] = [
  { key: "trainees", label: "Everyone" },
  { key: "add", label: "Add people" },
  { key: "groups", label: "Groups" },
  { key: "access", label: "Exam access" },
];

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

  const state = useAsync(
    async (signal) => {
      const [trainees, cohorts, groups] = await Promise.all([
        listAllTrainees(orgSlug, signal),
        listCohorts(orgSlug, signal),
        listTraineeGroups(orgSlug, signal),
      ]);
      return { trainees, cohorts: cohorts.items, groups: groups.items };
    },
    [orgSlug],
  );

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
              tabs={TABS.map((tab) =>
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
                onChanged={state.reload}
              />
            ) : null}

            {section === "add" ? (
              <AddTraineePanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                canManage={canManage}
                onAdded={state.reload}
              />
            ) : null}

            {section === "groups" ? (
              <GroupsPanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                groups={data.groups}
                trainees={data.trainees}
                canManage={canManage}
                onChanged={state.reload}
              />
            ) : null}

            {section === "access" ? (
              <AccessPanel orgSlug={orgSlug} trainees={data.trainees} canManage={canManage} />
            ) : null}
          </>
        )}
      </AsyncBoundary>

      <p className="text-osce-caption text-b2b-mid">
        Looking for supervisors and admins?{" "}
        <TextLink themeType="b2b" href={hrefFor("/team")}>
          Go to the team
        </TextLink>
        .
      </p>
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
