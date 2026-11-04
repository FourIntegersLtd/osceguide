"use client";

import { useCallback, useMemo, useState } from "react";
import { Alert, AsyncBoundary, Button, b2bTokens, Panel } from "@/foundation/ui";
import Table, { type Column, type TableMore } from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import { errorMessage, useAsync, useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { formatWhen } from "@/domains/assess/team/chrome";
import type { Trainee } from "@/domains/assess/api";
import {
  grantEntitlement,
  listEntitlements,
  listExams,
  revokeEntitlement,
  type Entitlement,
} from "@/domains/assess/roster/api";
import { displayName, sortTrainees } from "@/domains/assess/roster/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * Exam access for a trainee between sittings.
 *
 * Exam day never needs this — a dispatched slot skips the gate — so what is
 * granted here is the practice a trainee does in their own time, which
 * otherwise runs out with the consumer free trial. The retiring institution
 * client had no screen for it at all: the endpoints existed and nothing called
 * them, and an institution asking for practice access had to email us.
 *
 * A grant is against an email address, not a roster row, because the
 * entitlement belongs to the person's account.
 *
 * The grants list is a server page at a time, searched in SQL: an
 * institution's grants can outgrow "load it all and filter in the browser"
 * the same way its roster can.
 */
export function AccessPanel({
  orgSlug,
  trainees,
  canManage,
}: {
  orgSlug: string;
  trainees: Trainee[];
  canManage: boolean;
}) {
  const w = useAssessWords();
  const exams = useAsync((signal) => listExams(orgSlug, signal), [orgSlug]);

  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);
  const pages = useCursorPages(
    (cursor, signal) => listEntitlements(orgSlug, signal, { cursor, search: query || null }),
    [orgSlug, query],
  );

  const [email, setEmail] = useState("");
  const [examCode, setExamCode] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const grant = useCallback(async () => {
    if (!email || !examCode) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await grantEntitlement(orgSlug, {
        email,
        examCode,
        // A date input gives a day; the API wants an instant.
        endsAt: endsAt ? new Date(`${endsAt}T23:59:59`).toISOString() : null,
      });
      setNotice(`${email} can now practise ${examCode}.`);
      pages.state.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, email, examCode, endsAt, pages.state]);

  const revoke = useCallback(
    async (entitlement: Entitlement) => {
      setError(null);
      try {
        await revokeEntitlement(orgSlug, entitlement.id);
        pages.state.reload();
      } catch (cause) {
        setError(errorMessage(cause));
      }
    },
    [orgSlug, pages.state],
  );

  return (
    <div className="space-y-6">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      {canManage ? (
        <Panel
          title="Grant exam access"
          description={`Lets ${w.trainees} practise between ${w.sittings}. They do not need it to take an exam they are booked on.`}
        >
          <form
            className="grid grid-cols-1 gap-4 sm:grid-cols-3"
            onSubmit={(event) => {
              event.preventDefault();
              void grant();
            }}
          >
            <div className="sm:col-span-2">
              <label
                htmlFor="assess-access-person"
                className="block text-osce-body font-semibold text-b2b-headline"
              >
                Who
              </label>
              <select
                id="assess-access-person"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className={`mt-2 ${b2bTokens.b2bInputBase}`}
                required
              >
                <option value="">Choose a {w.trainee}…</option>
                {sortTrainees(trainees).map((trainee) => (
                  <option key={trainee.id} value={trainee.email}>
                    {displayName(trainee)} ({trainee.email})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="assess-access-exam"
                className="block text-osce-body font-semibold text-b2b-headline"
              >
                Exam
              </label>
              <select
                id="assess-access-exam"
                value={examCode}
                onChange={(event) => setExamCode(event.target.value)}
                className={`mt-2 ${b2bTokens.b2bInputBase}`}
                required
              >
                <option value="">Choose…</option>
                {(exams.data?.items ?? []).map((exam) => (
                  <option key={exam.id} value={exam.code}>
                    {exam.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="assess-access-ends"
                className="block text-osce-body font-semibold text-b2b-headline"
              >
                Until (optional)
              </label>
              <input
                id="assess-access-ends"
                type="date"
                value={endsAt}
                onChange={(event) => setEndsAt(event.target.value)}
                className={`mt-2 ${b2bTokens.b2bInputBase}`}
              />
            </div>
            <div className="flex items-end sm:col-span-3">
              <Button
                type="submit"
                themeType="b2b"
                variant="commit"
                disabled={busy || !email || !examCode}
              >
                {busy ? "Granting…" : "Grant access"}
              </Button>
            </div>
          </form>
        </Panel>
      ) : null}

      <div>
        <label htmlFor="assess-access-search" className="sr-only">
          Search grants
        </label>
        <input
          id="assess-access-search"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by person or exam…"
          className={b2bTokens.b2bInputBase}
        />
      </div>

      <AsyncBoundary state={pages.state}>
        {(entitlements) =>
          entitlements.length === 0 && !query ? (
            <p className="text-osce-body text-b2b-mid">
              No practice access given yet. {w.Trainees} can still take every exam they are booked on.
            </p>
          ) : (
            <GrantsTable
              entitlements={entitlements}
              more={pages}
              trainees={trainees}
              canManage={canManage}
              onRevoke={(entitlement) => revoke(entitlement)}
            />
          )
        }
      </AsyncBoundary>
    </div>
  );
}

/**
 * Revoked and expired grants stay on the list.
 *
 * `live` is the field that gates, and it is not "was ever granted": the list
 * carries revoked and expired rows too. Showing them as granted is the exact
 * mistake that made an institution think somebody had access when the gate
 * said otherwise.
 */
function GrantsTable({
  entitlements,
  more,
  trainees,
  canManage,
  onRevoke,
}: {
  entitlements: Entitlement[];
  more: TableMore;
  trainees: Trainee[];
  canManage: boolean;
  onRevoke: (entitlement: Entitlement) => Promise<void>;
}) {
  /* A grant names a user account; the roster names a trainee. They meet at
     `Trainee.user_id`, which is null until the person has signed in — so a
     grant to somebody who has not yet accepted their invitation shows as the
     address it was made to rather than as a name that does not exist yet. */
  const byUserId = useMemo(
    () =>
      new Map(
        trainees
          .filter((trainee) => trainee.user_id)
          .map((trainee) => [trainee.user_id, trainee]),
      ),
    [trainees],
  );

  const whoLabel = useCallback(
    (entitlement: Entitlement) => {
      const trainee = byUserId.get(entitlement.user_id);
      return trainee ? displayName(trainee) : "Not on this roster";
    },
    [byUserId],
  );

  const columns = useMemo<Column<Entitlement>[]>(
    () => [
      {
        header: "Who",
        key: (entitlement) => (
          <span className={cn(b2cTableCellText, "font-medium")}>{whoLabel(entitlement)}</span>
        ),
        priority: "primary",
      },
      {
        header: "Exam",
        key: (entitlement) => <span className="text-b2b-graphite">{entitlement.exam_code}</span>,
      },
      {
        header: "Status",
        key: (entitlement) =>
          entitlement.live ? (
            <span className="text-osce-caption font-medium text-b2b-success-text">Live</span>
          ) : (
            <span className="text-osce-caption font-medium text-b2b-warning-text/90">
              {entitlement.revoked_at ? "Revoked" : "Expired"}
            </span>
          ),
      },
      {
        header: "From",
        key: (entitlement) => <span className="text-b2b-mid">{formatWhen(entitlement.starts_at)}</span>,
        priority: "detail",
      },
      {
        header: "Until",
        key: (entitlement) => (
          <span className="text-b2b-mid">
            {entitlement.ends_at ? formatWhen(entitlement.ends_at) : "No end date"}
          </span>
        ),
        priority: "detail",
      },
      {
        header: "Actions",
        key: (entitlement) =>
          canManage && entitlement.live ? (
            <Button themeType="b2b" variant="secondary" size="sm" onClick={() => onRevoke(entitlement)}>
              Revoke
            </Button>
          ) : null,
      },
    ],
    [whoLabel, canManage, onRevoke],
  );

  return (
    <Table<Entitlement>
      rows={entitlements}
      more={more}
      themeType="b2b"
      columns={columns}
      idField="id"
      minWidthClassName="min-w-[640px]"
      empty={{ title: "No grants match." }}
    />
  );
}
