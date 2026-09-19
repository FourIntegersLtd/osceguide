"use client";

import { useCallback, useState } from "react";
import { HiOutlineKey } from "react-icons/hi2";
import { Alert, AsyncBoundary, Button, b2bTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { PanelCard, formatWhen } from "@/domains/assess/team/chrome";
import type { Trainee } from "@/domains/assess/api";
import {
  grantEntitlement,
  listEntitlements,
  listExams,
  revokeEntitlement,
  type Entitlement,
} from "@/domains/assess/roster/api";
import { displayName, sortTrainees } from "@/domains/assess/roster/support";

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
  const state = useAsync(
    async (signal) => {
      const [entitlements, exams] = await Promise.all([
        listEntitlements(orgSlug, signal),
        listExams(orgSlug, signal),
      ]);
      return { entitlements: entitlements.items, exams: exams.items };
    },
    [orgSlug],
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
      state.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, email, examCode, endsAt, state]);

  const revoke = useCallback(
    async (entitlement: Entitlement) => {
      setError(null);
      try {
        await revokeEntitlement(orgSlug, entitlement.id);
        state.reload();
      } catch (cause) {
        setError(errorMessage(cause));
      }
    },
    [orgSlug, state],
  );

  return (
    <AsyncBoundary state={state}>
      {(data) => (
        <div className="space-y-6">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          {notice ? <Alert tone="success">{notice}</Alert> : null}

          {canManage ? (
            <PanelCard
              title="Grant exam access"
              subtitle="For practice between sittings. An exam-day slot does not need a grant."
              icon={<HiOutlineKey className="h-5 w-5" aria-hidden />}
            >
              <form
                className="grid gap-4 sm:grid-cols-3"
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
                    <option value="">Choose a trainee…</option>
                    {sortTrainees(trainees).map((trainee) => (
                      <option key={trainee.id} value={trainee.email}>
                        {displayName(trainee)} — {trainee.email}
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
                    {data.exams.map((exam) => (
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
            </PanelCard>
          ) : null}

          <GrantsTable
            entitlements={data.entitlements}
            trainees={trainees}
            canManage={canManage}
            onRevoke={(entitlement) => void revoke(entitlement)}
          />
        </div>
      )}
    </AsyncBoundary>
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
  trainees,
  canManage,
  onRevoke,
}: {
  entitlements: Entitlement[];
  trainees: Trainee[];
  canManage: boolean;
  onRevoke: (entitlement: Entitlement) => void;
}) {
  /* A grant names a user account; the roster names a trainee. They meet at
     `Trainee.user_id`, which is null until the person has signed in — so a
     grant to somebody who has not yet accepted their invitation shows as the
     address it was made to rather than as a name that does not exist yet. */
  const byUserId = new Map(
    trainees.filter((trainee) => trainee.user_id).map((trainee) => [trainee.user_id, trainee]),
  );
  if (entitlements.length === 0) {
    return (
      <p className="text-osce-body text-b2b-mid">
        Nothing granted yet. Trainees still sit everything they are rostered onto.
      </p>
    );
  }

  return (
    <div className={b2bTokens.b2bGroupedShell}>
      <div className={b2bTokens.b2bTableScroll}>
        <table className="min-w-full w-full divide-y divide-b2b-border">
          <thead>
            <tr>
              {["Who", "Exam", "Status", "From", "Until", ""].map((header, index) => (
                <th
                  key={header || index}
                  scope="col"
                  className="px-4 py-2 text-left text-osce-caption font-medium text-b2b-mid"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-b2b-border">
            {entitlements.map((entitlement) => (
              <tr key={entitlement.id}>
                <td className="px-4 py-3 text-osce-body font-medium text-b2b-headline">
                  {(() => {
                    const trainee = byUserId.get(entitlement.user_id);
                    return trainee ? displayName(trainee) : "Not on this roster";
                  })()}
                </td>
                <td className="px-4 py-3 text-osce-body text-b2b-graphite">
                  {entitlement.exam_code}
                </td>
                <td className="px-4 py-3 text-osce-body">
                  {entitlement.live ? (
                    <span className="text-osce-caption font-medium text-b2b-success-text">
                      Live
                    </span>
                  ) : (
                    <span className="text-osce-caption font-medium text-b2b-warning-text/90">
                      {entitlement.revoked_at ? "Revoked" : "Expired"}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-osce-body text-b2b-mid">
                  {formatWhen(entitlement.starts_at)}
                </td>
                <td className="px-4 py-3 text-osce-body text-b2b-mid">
                  {entitlement.ends_at ? formatWhen(entitlement.ends_at) : "No end date"}
                </td>
                <td className="px-4 py-3 text-right">
                  {canManage && entitlement.live ? (
                    <Button
                      themeType="b2b"
                      variant="secondary"
                      size="sm"
                      onClick={() => onRevoke(entitlement)}
                    >
                      Revoke
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
