"use client";

import type { AssessWords } from "@/domains/assess/vocabulary";
import { useState } from "react";
import { AsyncBoundary, Button, B2CHero, B2CPageHeader, LoadMore } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { TabStrip } from "@/domains/assess/team/chrome";
import { MembersPanel } from "@/domains/assess/team/MembersPanel";
import { ActivityPanel } from "@/domains/assess/team/ActivityPanel";
import { TraineesPanel } from "@/domains/assess/roster/TraineesPanel";
import { GroupsPanel } from "@/domains/assess/roster/GroupsPanel";
import { AccessPanel } from "@/domains/assess/roster/AccessPanel";
import { useRosterData } from "@/domains/assess/roster/useRosterData";
import type { Trainee } from "@/domains/assess/api";
import { AddPeopleSheet, type AddKind } from "@/domains/assess/people/AddPeopleSheet";
import { peopleTabs, type PeopleTab } from "@/domains/assess/people/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * People: everyone in the organisation, on one page. Trainees sit sittings; staff
 * (supervisors and admins) run circuits and mark them. This is the old roster and
 * the old team screen under one set of tabs, with one "Add people" sheet.
 *
 * The header and tabs sit outside the roster load, so Staff and History do not
 * wait on it; only the tabs that read the roster sit inside the boundary.
 */
export function People({ orgSlug, initialTab }: { orgSlug: string; initialTab: PeopleTab }) {
  const w = useAssessWords();
  const { session } = useSession();
  const canManage = can(session, "manage_team");
  const tabs = peopleTabs({ manageTeam: canManage }, w);
  const [tab, setTab] = useState<PeopleTab>(
    tabs.some((candidate) => candidate.key === initialTab) ? initialTab : "trainees",
  );
  const [adding, setAdding] = useState<AddKind | null>(null);
  // Bumped after a staff add so the staff list refetches.
  const [staffKey, setStaffKey] = useState(0);

  const { state, reloadAfter, trainees, hasMore, loadMore, loadingMore, moreError } =
    useRosterData(orgSlug);
  const loadedAll = !hasMore;

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title={w.People}
        subtitle={`Everyone in your organisation. ${w.Trainees} sit ${w.sittings}; staff (supervisors and admins) run circuits and mark them.`}
        action={
          canManage ? (
            <Button
              themeType="b2b"
              variant="commit"
              onClick={() => setAdding(tab === "staff" ? "staff" : "trainees")}
            >
              {w.addPeople}
            </Button>
          ) : null
        }
      />

      {!canManage ? (
        <p className="text-osce-caption text-b2b-mid">
          <span className="font-medium">Supervisor (read only)</span>. Only an owner or admin can
          add {w.trainees}. Ask one of them to add the people you need on the roster.
        </p>
      ) : null}

      <TabStrip
        tabs={tabs.map((entry) =>
          entry.key === "trainees" ? { ...entry, count: trainees.total } : entry,
        )}
        active={tab}
        onSelect={setTab}
        label="People sections"
      />

      {tab === "staff" ? (
        <MembersPanel
          key={staffKey}
          orgSlug={orgSlug}
          canManage={canManage}
          onInviteStaff={() => setAdding("staff")}
        />
      ) : null}
      {tab === "history" ? <ActivityPanel orgSlug={orgSlug} /> : null}

      {tab === "trainees" || tab === "groups" || tab === "access" ? (
        <AsyncBoundary state={state}>
          {(data) => (
            <>
              {tab === "trainees" ? (
                <>
                  {trainees.total > 0 ? (
                    <B2CHero title={rosterHeadline(trainees.rows, trainees.total, loadedAll, w)}>
                      {loadedAll ? rosterDetail(trainees.rows) : null}
                    </B2CHero>
                  ) : null}
                  <TraineesPanel
                    orgSlug={orgSlug}
                    cohorts={data.cohorts}
                    groups={data.groups}
                    canManage={canManage}
                    onAddPeople={() => setAdding("trainees")}
                    onChanged={reloadAfter("trainees", "groups")}
                  />
                  {canManage ? (
                    <p className="text-osce-caption text-b2b-mid">
                      Looking for supervisors and admins? They are on the{" "}
                      <button type="button" className="underline" onClick={() => setTab("staff")}>
                        Staff
                      </button>{" "}
                      tab.
                    </p>
                  ) : null}
                </>
              ) : null}

              {tab === "groups" ? (
                <GroupsPanel
                  orgSlug={orgSlug}
                  cohorts={data.cohorts}
                  groups={data.groups}
                  trainees={trainees.rows}
                  canManage={canManage}
                  onChanged={reloadAfter("groups", "cohorts")}
                />
              ) : null}

              {tab === "access" ? (
                <AccessPanel orgSlug={orgSlug} trainees={trainees.rows} canManage={canManage} />
              ) : null}

              {(tab === "groups" || tab === "access") && (hasMore || moreError) ? (
                <div className="flex flex-col items-center gap-1">
                  <p className="text-osce-caption text-b2b-mid">
                    Showing {trainees.rows.length} of {trainees.total} {w.trainees}.
                  </p>
                  <LoadMore hasMore={hasMore} busy={loadingMore} onLoad={loadMore} error={moreError} />
                </div>
              ) : null}

            </>
          )}
        </AsyncBoundary>
      ) : null}

      {adding ? (
        <AddPeopleSheet
          orgSlug={orgSlug}
          initialKind={adding}
          cohorts={state.data?.cohorts ?? []}
          canManage={canManage}
          onTraineesAdded={reloadAfter("trainees", "groups", "cohorts")}
          onStaffAdded={() => setStaffKey((key) => key + 1)}
          onClose={() => setAdding(null)}
        />
      ) : null}
    </div>
  );
}

function programmeCount(trainees: Trainee[]): number {
  return new Set(trainees.flatMap((trainee) => trainee.programme_names ?? [])).size;
}

/** "N trainees across M programmes", counting only programmes someone is rostered on. */
function rosterHeadline(trainees: Trainee[], total: number, loadedAll: boolean, words: AssessWords): string {
  const people = `${total} ${total === 1 ? words.trainee : words.trainees}`;
  // Programmes are read off the rows, so they are only the whole truth once every row is here.
  if (!loadedAll) return people;
  const count = programmeCount(trainees);
  return `${people} across ${count} ${count === 1 ? "programme" : "programmes"}`;
}

function rosterDetail(trainees: Trainee[]): string {
  const sat = trainees.reduce((total, trainee) => total + trainee.stations_sat, 0);
  return `${sat} ${sat === 1 ? "station" : "stations"} sat so far.`;
}
