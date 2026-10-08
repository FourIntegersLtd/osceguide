"use client";

import { useState } from "react";
import { AsyncBoundary, Button, B2CHero, B2CPageHeader, LoadMore, TextLink } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { TabStrip } from "@/domains/assess/team/chrome";
import { TraineesPanel } from "@/domains/assess/roster/TraineesPanel";
import { AddTraineePanel } from "@/domains/assess/roster/AddTraineePanel";
import { GroupsPanel } from "@/domains/assess/roster/GroupsPanel";
import { AccessPanel } from "@/domains/assess/roster/AccessPanel";
import type { Trainee } from "@/domains/assess/api";
import { rosterTabs, sectionSubtitle } from "@/domains/assess/roster/support";
import { useRosterData } from "@/domains/assess/roster/useRosterData";

type Section = "trainees" | "add" | "groups" | "access";

/**
 * The roster: who the organisation examines.
 *
 * Separate from Team, which is the staff who run the examination. The three
 * lists are loaded once for the whole screen rather than per tab — the old
 * client had each of these as its own route and refetched the roster on every
 * visit — and a write reloads only the lists it changed (`useRosterData`).
 */
export function Trainees({ orgSlug }: { orgSlug: string }) {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const [section, setSection] = useState<Section>("trainees");
  const canManage = can(session, "manage_team");

  const { state, reloadAfter, trainees, hasMore, loadMore, loadingMore, moreError } = useRosterData(orgSlug);
  const loadedAll = !hasMore;

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(data) => (
          <>
            <B2CPageHeader
              title="People"
              subtitle={sectionSubtitle(section, {
                trainees: trainees.total,
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

            {section === "trainees" && trainees.total > 0 ? (
              <B2CHero title={rosterHeadline(trainees.rows, trainees.total, loadedAll)}>
                {loadedAll ? rosterDetail(trainees.rows) : null}
              </B2CHero>
            ) : null}

            <TabStrip
              tabs={rosterTabs(canManage).map((tab) =>
                tab.key === "trainees" ? { ...tab, count: trainees.total } : tab,
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
                onAdded={reloadAfter("trainees", "groups", "cohorts")}
              />
            ) : null}

            {section === "groups" ? (
              <GroupsPanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                groups={data.groups}
                trainees={trainees.rows}
                canManage={canManage}
                onChanged={reloadAfter("groups", "cohorts")}
              />
            ) : null}

            {section === "access" ? (
              <AccessPanel orgSlug={orgSlug} trainees={trainees.rows} canManage={canManage} />
            ) : null}

            {(section === "groups" || section === "access") && (hasMore || moreError) ? (
              <div className="flex flex-col items-center gap-1">
                <p className="text-osce-caption text-b2b-mid">
                  Showing {trainees.rows.length} of {trainees.total} trainees.
                </p>
                <LoadMore hasMore={hasMore} busy={loadingMore} onLoad={loadMore} error={moreError} />
              </div>
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
function rosterHeadline(trainees: Trainee[], total: number, loadedAll: boolean): string {
  const people = `${total} ${total === 1 ? "trainee" : "trainees"}`;
  // Programmes are read off the rows, so they are only the whole truth once every row is here.
  if (!loadedAll) return people;
  const count = programmeCount(trainees);
  return `${people} across ${count} ${count === 1 ? "programme" : "programmes"}`;
}

function rosterDetail(trainees: Trainee[]): string {
  const sat = trainees.reduce((total, trainee) => total + trainee.stations_sat, 0);
  return `${sat} ${sat === 1 ? "station" : "stations"} sat so far.`;
}
