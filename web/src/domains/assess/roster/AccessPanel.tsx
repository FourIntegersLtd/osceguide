"use client";

import { say } from "@/domains/assess/roster/rosterWords";
import { LuBan } from "react-icons/lu";
import { RowAction, RowActions } from "@/foundation/ui";
import { useCallback, useMemo, useState } from "react";
import { AsyncBoundary, b2bTokens as t, cn } from "@/foundation/ui";
import { Chip, Note, card, fields, h2, row, th } from "@/domains/assess/ui";
import { errorMessage, useAsync, useCursorPages, useSearchQuery } from "@/foundation/hooks";
import type { Trainee } from "@/domains/assess/api";
import {
  grantEntitlement,
  listEntitlements,
  listExams,
  revokeEntitlement,
  type Entitlement,
} from "@/domains/assess/roster/api";
import { displayName, shortDay, sortTrainees } from "@/domains/assess/roster/support";
import { useAssessWords } from "@/capabilities/assess-words";
import { boardBtn, boardPadWide, boardInput, boardLabel, boardButtonSmall } from "@/foundation/ui/boardKit";

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
    <div className="flex flex-col gap-6">
      {error ? <Note tone="bad">{error}</Note> : null}

      {canManage ? (
        <form
          className={boardPadWide}
          onSubmit={(event) => {
            event.preventDefault();
            void grant();
          }}
        >
          <h2 className={h2}>Give exam access</h2>
          <p className={cn(t.assessMeta, "m-0")}>
            {`Lets ${w.trainees} practise between ${w.sittings}. They do not need it to take an exam they are booked on.`}
          </p>
          <div className={fields}>
            <div>
              <label htmlFor="assess-access-person" className={boardLabel}>
                Who
              </label>
              <select id="assess-access-person" value={email} onChange={(event) => setEmail(event.target.value)} className={boardInput} required>
                <option value="">Choose a {w.trainee}…</option>
                {sortTrainees(trainees).map((trainee) => (
                  <option key={trainee.id} value={trainee.email}>
                    {sameNameAsAnother(trainees, trainee) ? `${displayName(trainee)} (${trainee.email})` : displayName(trainee)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="assess-access-exam" className={boardLabel}>
                Exam
              </label>
              <select id="assess-access-exam" value={examCode} onChange={(event) => setExamCode(event.target.value)} className={boardInput} required>
                <option value="">Choose…</option>
                {(exams.data?.items ?? []).map((exam) => (
                  <option key={exam.id} value={exam.code}>
                    {exam.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="assess-access-ends" className={boardLabel}>
                Until (optional)
              </label>
              <input id="assess-access-ends" type="date" value={endsAt} onChange={(event) => setEndsAt(event.target.value)} className={boardInput} />
            </div>
          </div>
          <button type="submit" className={cn(boardBtn("primary"), "self-start")} disabled={busy || !email || !examCode}>
            {busy ? "Granting…" : "Grant access"}
          </button>
        </form>
      ) : null}

      {notice ? <Note tone="ok">{notice}</Note> : null}

      <input
        id="assess-access-search"
        type="search"
        aria-label="Search grants"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={say(w, "Search by person or exam…")}
        className={cn(boardInput, "max-w-[360px]")}
      />

      <AsyncBoundary state={pages.state}>
        {(entitlements) =>
          entitlements.length === 0 && !query ? (
            <p className={cn(t.assessMeta, "m-0")}>
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
  more: { hasMore: boolean; loadingMore: boolean; moreError: Error | null; loadMore: () => void };
  trainees: Trainee[];
  canManage: boolean;
  onRevoke: (entitlement: Entitlement) => Promise<void>;
}) {
  const w = useAssessWords();
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
    (entitlement: Entitlement) => byUserId.get(entitlement.user_id)?.email ?? say(w, "Not on this roster"),
    [byUserId, w],
  );

  if (entitlements.length === 0) {
    return (
      <div className={boardPadWide}>
        <div className={t.assessMeta}>Search with no match</div>
        <div>No grants match.</div>
      </div>
    );
  }

  return (
    <div role="table" className={card}>
      <div role="row" className={th}>
        <span className="flex-[1_1_180px]">Who</span>
        <span className="w-[100px]">Exam</span>
        <span className="w-20">Status</span>
        <span className="w-[90px]">From</span>
        <span className="w-[110px]">Until</span>
        <span className="w-20">Actions</span>
      </div>
      {entitlements.map((entitlement) => (
        <div key={entitlement.id} role="row" className={row}>
          <span className="flex-[1_1_180px]">{whoLabel(entitlement)}</span>
          <span className="w-[100px]">{entitlement.exam_code}</span>
          <span className="w-20">
            {entitlement.live ? <Chip tone="ok">Live</Chip> : <Chip>{entitlement.revoked_at ? "Revoked" : "Expired"}</Chip>}
          </span>
          <span className="w-[90px]">{shortDay(entitlement.starts_at)}</span>
          <span className="w-[110px]">{entitlement.ends_at ? shortDay(entitlement.ends_at) : "No end date"}</span>
          {canManage && entitlement.live ? (
            <RowActions>
              <RowAction label="Revoke" onClick={() => void onRevoke(entitlement)}>
                <LuBan className="h-4 w-4" aria-hidden />
              </RowAction>
            </RowActions>
          ) : (
            <span className="w-20" />
          )}
        </div>
      ))}
      {more.hasMore || more.moreError ? (
        <div className={cn(row, "justify-center")}>
          <button type="button" className={boardButtonSmall} disabled={more.loadingMore} onClick={more.loadMore}>
            {more.loadingMore ? "Loading…" : "Load more"}
          </button>
          {more.moreError ? <span className="text-osce-danger-text">{more.moreError.message}</span> : null}
        </div>
      ) : null}
    </div>
  );
}

/** The board lists names only; two people who share one need their address to tell them apart. */
function sameNameAsAnother(all: Trainee[], one: Trainee): boolean {
  return all.some((other) => other.id !== one.id && displayName(other) === displayName(one));
}
