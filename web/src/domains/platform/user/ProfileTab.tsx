"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { listExams } from "@/capabilities/stations/api";
import { resetUserPassword, updateUser, type PlatformUserDetail } from "@/domains/platform/api";
import { formatDay } from "@/domains/platform/support";

const selectClass =
  "w-full rounded-md border border-b2c-border bg-osce-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-osce-accent/20";

/**
 * The retiring console's "Basic information" card, as a form that saves.
 *
 * The exam is a select over the catalogue rather than a free code, because a
 * mistyped code is an account that opens on nothing. The exam date and the
 * reading arrangement are the two fields the old card showed that nothing on
 * the platform wrote until now.
 */
export function ProfileTab({
  user,
  onSaved,
}: {
  user: PlatformUserDetail;
  onSaved: (user: PlatformUserDetail) => void;
}) {
  const toast = useToast();
  const exams = useAsync((signal) => listExams(signal), []);
  const [name, setName] = useState(user.name);
  const [examCode, setExamCode] = useState(user.exam_code ?? "");
  const [examDate, setExamDate] = useState(user.exam_date ?? "");
  const [extraReading, setExtraReading] = useState(String(user.extra_reading_percent ?? 0));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const percent = Number(extraReading);
      const updated = await updateUser(user.id, {
        name: name.trim() || null,
        exam_code: examCode.trim() || null,
        exam_date: examDate || null,
        extra_reading_percent: Number.isFinite(percent) ? Math.round(percent) : null,
      });
      onSaved(updated);
      toast.success("Profile saved");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [user.id, name, examCode, examDate, extraReading, onSaved, toast]);

  const reset = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await resetUserPassword(user.id);
      toast.success("Password reset emailed", "If the account exists, they will receive a link.");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [user.id, toast]);

  return (
    <Card padding="md">
      <div className="flex max-w-lg flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} disabled={busy} />
        <AsyncBoundary state={exams} isEmpty={() => false}>
          {(page) => (
            <label className="flex flex-col gap-1 text-sm text-ink">
              <span className="text-xs font-medium text-ink-muted">Exam</span>
              <select
                className={selectClass}
                value={examCode}
                onChange={(e) => setExamCode(e.target.value)}
                disabled={busy}
              >
                <option value="">No exam chosen</option>
                {page.items.map((exam) => (
                  <option key={exam.code} value={exam.code}>
                    {exam.name} ({exam.code.toUpperCase()})
                  </option>
                ))}
                {examCode && !page.items.some((exam) => exam.code === examCode) ? (
                  <option value={examCode}>{examCode} (not in the catalogue)</option>
                ) : null}
              </select>
              <span className="text-xs text-ink-subtle">The exam this account opens on. Access is on the Entitlements tab.</span>
            </label>
          )}
        </AsyncBoundary>
        <Input
          type="date"
          label="Exam date"
          value={examDate}
          onChange={(e) => setExamDate(e.target.value)}
          disabled={busy}
          hint="When they sit the real thing. The dashboard counts down to it."
        />
        <Input
          type="number"
          min={0}
          max={100}
          inputMode="numeric"
          label="Extra reading time (%)"
          value={extraReading}
          onChange={(e) => setExtraReading(e.target.value)}
          disabled={busy}
          hint="An access arrangement. 25 is what the old client’s bare yes meant; 0 is none."
        />
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-ink-subtle">
          <dt>Member since</dt>
          <dd className="text-ink-muted">{formatDay(user.created_at)}</dd>
          <dt>Last sign-in</dt>
          <dd className="text-ink-muted">{user.last_login_at ? formatDay(user.last_login_at) : "Never"}</dd>
          {user.must_change_password ? (
            <>
              <dt>Password</dt>
              <dd className="text-ink-muted">Must be changed on next sign-in</dd>
            </>
          ) : null}
        </dl>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" disabled={busy} onClick={() => void reset()}>
            Send password reset
          </Button>
          <Button disabled={busy} onClick={() => void save()}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
