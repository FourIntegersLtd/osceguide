"use client";

import { boardCard, boardTab, boardTabs, boardBtn } from "@/foundation/ui/boardKit";
import { useState } from "react";
import { AsyncBoundary, LoadMore, b2bTokens as t, cn } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { readOrgDashboard } from "@/domains/assess/dashboard/api";
import { can, useSession } from "@/foundation/session";
import { Note } from "@/domains/assess/ui";
import { MembersPanel } from "@/domains/assess/team/MembersPanel";
import { ActivityPanel } from "@/domains/assess/team/ActivityPanel";
import { TraineesPanel } from "@/domains/assess/roster/TraineesPanel";
import { GroupsPanel } from "@/domains/assess/roster/GroupsPanel";
import { AccessPanel } from "@/domains/assess/roster/AccessPanel";
import { useRosterData } from "@/domains/assess/roster/useRosterData";
import type { Trainee } from "@/domains/assess/api";
import { AddPeopleSheet, type AddKind } from "@/domains/assess/people/AddPeopleSheet";
import { peopleHeader, peopleTabs, type PeopleTab } from "@/domains/assess/people/support";
import { AddCandidatesDialog } from "@/domains/assess/people/AddCandidatesDialog";
import { BulkImportDialog } from "@/domains/assess/roster/BulkImportDialog";
import { say } from "@/domains/assess/roster/rosterWords";
import { useAssessWords, type AssessWords } from "@/capabilities/assess-words";

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
  // Hire adds candidates in a dialog (HireCandidates.dc.html); its spreadsheet is the same import dialog.
  // Bumped after a dialog add so the candidate list, which pages itself, reads again.
  const [listKey, setListKey] = useState(0);
  const [dialog, setDialog] = useState<"emails" | "sheet" | null>(null);
  // Bumped after a staff add so the staff list refetches.
  const [staffKey, setStaffKey] = useState(0);

  const { state, reloadAfter, trainees, hasMore, loadMore, loadingMore, moreError } =
    useRosterData(orgSlug);
  const loadedAll = !hasMore;

  const org = useAsync((signal) => readOrgDashboard(orgSlug, signal), [orgSlug]);
  const orgName = org.data?.name ?? "your organisation";
  const header = peopleHeader(tab, w, orgName);
  const refreshAfterAdd = () => {
    reloadAfter("trainees", "groups", "cohorts")();
    setListKey((key) => key + 1);
  };
  const openAdd = (kind: AddKind) => (w.hiring && kind === "trainees" ? setDialog("emails") : setAdding(kind));

  if (adding) {
    return (
      <AddPeopleSheet
        orgSlug={orgSlug}
        initialKind={adding}
        cohorts={state.data?.cohorts ?? []}
        canManage={canManage}
        onTraineesAdded={reloadAfter("trainees", "groups", "cohorts")}
        onStaffAdded={() => setStaffKey((key) => key + 1)}
        onClose={() => setAdding(null)}
      />
    );
  }

  return (
    <div className="flex min-w-0 flex-col gap-6" data-testid="people-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className={t.assessEyebrow}>{header.eyebrow}</div>
          <h1 className={t.assessTitle}>{header.title}</h1>
          <p className={cn(t.assessDesc, "m-0")}>{header.desc}</p>
        </div>
        {canManage ? (
          <div className="flex flex-wrap items-center gap-2.5">
            <button type="button" className={boardBtn("primary")} onClick={() => openAdd(header.action.opens)}>
              {header.action.label}
            </button>
          </div>
        ) : null}
      </div>

      {!canManage ? (
        <Note tone="warn">
          <b>{w.Supervisor} (read only)</b>. Only an owner or admin can add {w.trainees}. {say(w, "Ask one of them to add the people you need on the roster.")}
        </Note>
      ) : null}

      <div className={boardTabs} role="tablist" aria-label="People sections">
        {tabs.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            aria-selected={tab === entry.key}
            onClick={() => setTab(entry.key)}
            className={boardTab(tab === entry.key)}
          >
            {entry.label}
          </button>
        ))}
      </div>

      {tab === "staff" ? (
        <MembersPanel
          key={staffKey}
          orgSlug={orgSlug}
          canManage={canManage}
          onInviteStaff={() => openAdd("staff")}
        />
      ) : null}
      {tab === "history" ? <ActivityPanel orgSlug={orgSlug} /> : null}

      {tab === "trainees" || tab === "groups" || tab === "access" ? (
        <AsyncBoundary state={state}>
          {(data) => (
            <>
              {tab === "trainees" ? (
                <>
                  {trainees.total > 0 && !w.hiring ? (
                    <div className={cn(boardCard, "flex flex-wrap items-center justify-between gap-5 p-6")}>
                      <div>
                        <h2 className="m-0 text-assess-hero font-semibold text-osce-ink-900">
                          {rosterHeadline(trainees.rows, trainees.total, loadedAll, w)}
                        </h2>
                        {loadedAll ? <div className={t.assessMeta}>{rosterDetail(trainees.rows)}</div> : null}
                      </div>
                    </div>
                  ) : null}
                  <TraineesPanel
                    key={listKey}
                    orgSlug={orgSlug}
                    cohorts={data.cohorts}
                    groups={data.groups}
                    canManage={canManage}
                    onAddPeople={() => openAdd("trainees")}
                    onChanged={reloadAfter("trainees", "groups")}
                  />
                  {canManage ? (
                    <p className={cn(t.assessMeta, "m-0")}>
                      {w.hiring ? "Looking for assessors? They are on the" : "Looking for supervisors and admins? They are on the"}{" "}
                      <button type="button" className="text-osce-accent hover:text-osce-accent-hover" onClick={() => setTab("staff")}>
                        {w.hiring ? w.Supervisors : "Staff"}
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


      {w.hiring ? (
        <>
          <AddCandidatesDialog
            orgSlug={orgSlug}
            open={dialog === "emails"}
            cohorts={state.data?.cohorts ?? []}
            existingEmails={trainees.rows.map((row) => row.email)}
            onClose={() => setDialog(null)}
            onAdded={refreshAfterAdd}
            onSpreadsheet={() => setDialog("sheet")}
            onOne={() => {
              setDialog(null);
              setAdding("trainees");
            }}
          />
          <BulkImportDialog
            orgSlug={orgSlug}
            open={dialog === "sheet"}
            cohorts={state.data?.cohorts ?? []}
            onClose={() => setDialog(null)}
            onImported={refreshAfterAdd}
          />
        </>
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
