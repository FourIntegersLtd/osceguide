"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CHero,
  B2CPageHeader,
  B2CSegmentedTabs,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { plural } from "@/foundation/format";
import { useSurface } from "@/capabilities";
import { listPlans } from "@/capabilities/account/api";
import {
  readDirectorySummary,
  type DirectoryFilters as Filters,
  type DirectorySummary,
} from "@/domains/platform/api";
import { DirectoryFilters } from "@/domains/platform/users/DirectoryFilters";
import { UserGroup } from "@/domains/platform/users/UserGroup";
import {
  directoryListingTotal,
  groupTitle,
} from "@/domains/platform/users/vocabulary";

const NONE: Filters = {
  q: null,
  examCode: null,
  status: null,
  access: null,
  planCode: null,
};

/**
 * The account directory: everyone, one tab per exam, with the retiring B2C
 * admin's columns and filters.
 *
 * That console had a page per exam because each exam was its own database.
 * Here an account is one row whatever it holds, so each exam is a tab over
 * one table, paging on its own, and the counts across the top come
 * from one summary call rather than from having loaded everybody.
 */
export function Users() {
  const { hrefFor } = useSurface();
  const [filters, setFilters] = useState<Filters>(NONE);
  const [term, setTerm] = useState("");
  const summary = useAsync((signal) => readDirectorySummary(signal), []);
  const plans = useAsync(
    async (signal) => (await listPlans(signal)).items.map((plan) => plan.code),
    [],
  );

  const clear = () => {
    setTerm("");
    setFilters(NONE);
  };

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader title="Users" />

      {plans.error ? (
        <Alert tone="danger">Could not load the plans for the filter: {errorMessage(plans.error)}</Alert>
      ) : null}

      <AsyncBoundary state={summary}>
        {(counts) => (
          <>
            <B2CHero title={plural(counts.total, "account")}>
              {counts.paid} paid · {counts.trial} on trial
            </B2CHero>
            <DirectoryFilters
              plans={plans.data ?? []}
              filters={filters}
              term={term}
              onTerm={setTerm}
              onChange={setFilters}
            />
            <Groups
              summary={counts}
              filters={filters}
              hrefFor={hrefFor}
              onClear={clear}
            />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

/** The tab for accounts with no exam set; no exam code can collide with it. */
const UNASSIGNED_TAB = "__unassigned";
/** The tab across every exam, so a search can find someone whatever they are on. */
const ALL_TAB = "__all";

function Groups({
  summary,
  filters,
  hrefFor,
  onClear,
}: {
  summary: DirectorySummary;
  filters: Filters;
  hrefFor: (path: string) => string;
  onClear: () => void;
}) {
  // Busiest exam first. Exams nobody is on yet are one line under the tabs
  // rather than a run of empty tabs.
  const populated = summary.exams
    .filter((exam) => exam.users > 0)
    .sort((a, b) => b.users - a.users);
  const empty = summary.exams.filter((exam) => exam.users === 0);
  const tabs = [
    { id: ALL_TAB, label: `All accounts · ${summary.total}` },
    ...populated.map((exam) => ({
      id: exam.code,
      label: `${exam.name || exam.code.toUpperCase()} · ${exam.users}`,
    })),
    { id: UNASSIGNED_TAB, label: `No exam set · ${summary.unassigned}` },
  ];
  const firstTab = ALL_TAB;
  const [chosen, setChosen] = useState<string>(firstTab);
  // The chosen tab can vanish when the summary reloads; fall back to the first.
  const active = tabs.some((tab) => tab.id === chosen) ? chosen : firstTab;
  const exam = populated.find((entry) => entry.code === active);

  return (
    <>
      <B2CSegmentedTabs
        aria-label="Exam"
        items={tabs}
        value={active}
        onChange={setChosen}
      />
      {active === ALL_TAB ? (
        <UserGroup
          key={ALL_TAB}
          title={`All accounts · ${summary.total}`}
          description={`${summary.paid} paid · ${summary.trial} on trial`}
          filters={{ ...filters, examCode: null }}
          hrefFor={hrefFor}
          totalCount={directoryListingTotal(summary, { ...filters, examCode: null })}
          onClear={onClear}
        />
      ) : exam ? (
        <UserGroup
          key={exam.code}
          title={groupTitle(exam.code, exam.name, exam.users)}
          description={`Of everyone on this exam: ${exam.paid} paid · ${exam.trial} on trial · ${exam.not_started} not started`}
          filters={{ ...filters, examCode: exam.code }}
          hrefFor={hrefFor}
          totalCount={directoryListingTotal(summary, {
            ...filters,
            examCode: exam.code,
          })}
          onClear={onClear}
        />
      ) : (
        <UserGroup
          key={UNASSIGNED_TAB}
          title={`No exam set on the account · ${summary.unassigned}`}
          description={`${summary.unassigned_paid} paid · ${summary.unassigned_trial} on trial. Staff accounts appear here too.`}
          filters={{ ...filters, examCode: null, unassigned: true }}
          hrefFor={hrefFor}
          totalCount={directoryListingTotal(summary, {
            ...filters,
            examCode: null,
            unassigned: true,
          })}
          onClear={onClear}
        />
      )}
      {empty.length > 0 ? (
        <p className="px-1 text-osce-meta text-ink-subtle">
          Nobody yet on{" "}
          {empty.map((entry) => entry.name || entry.code.toUpperCase()).join(", ")}
          .
        </p>
      ) : null}
    </>
  );
}
