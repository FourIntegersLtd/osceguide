"use client";

import { useCallback, useState } from "react";
import {
  ActionRail,
  Alert,
  AsyncBoundary,
  Button,
  Checkbox,
  DetailLayout,
  FactList,
  Input,
  Panel,
  Select,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { listExams } from "@/capabilities/stations/api";
import {
  resetUserPassword,
  updateUser,
  type PlatformUserDetail,
} from "@/domains/platform/api";
import { formatDay, formatMoment } from "@/domains/platform/support";

/**
 * Who the account is: the editable profile on the left, the record and the
 * password reset on the right. Payment, access and the console live on the
 * Account tab, so no fact is shown in two places.
 *
 * The exam is a select over the catalogue rather than a free code, because a
 * mistyped code is an account that opens on nothing.
 */
export function ProfileTab({
  user,
  onSaved,
}: {
  user: PlatformUserDetail;
  onSaved: (user: PlatformUserDetail) => void;
}) {
  return (
    <DetailLayout
      main={<ProfileForm user={user} onSaved={onSaved} />}
      rail={
        <>
          <Panel title="Record" padding="sm">
            <FactList columns={1} items={recordFacts(user)} />
          </Panel>
          <PasswordReset userId={user.id} />
        </>
      }
    />
  );
}

function recordFacts(
  user: PlatformUserDetail,
): { label: string; value: React.ReactNode }[] {
  const exam = (user.exam_code ?? "sca").toLowerCase();
  const legacyId =
    user.legacy_consumer_ids?.[exam] ??
    Object.values(user.legacy_consumer_ids ?? {})[0];
  const facts: { label: string; value: React.ReactNode }[] = [
    { label: "Member since", value: formatDay(user.created_at) },
    {
      label: "Last sign-in",
      value: user.last_login_at ? formatMoment(user.last_login_at) : "Never",
    },
    { label: "Role", value: user.consumer_role === "admin" ? "Admin" : "User" },
  ];
  if (user.must_change_password) {
    facts.push({ label: "Password", value: "Must be changed on next sign-in" });
  }
  if (legacyId) {
    facts.push({
      label: "Legacy id",
      value: <span className="font-mono">{legacyId}</span>,
    });
  }
  return facts;
}

function ProfileForm({
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
  const [extraTime, setExtraTime] = useState(user.needs_extra_time ?? false);
  const [readingSeconds, setReadingSeconds] = useState(
    String(user.custom_reading_seconds ?? ""),
  );
  const [simulationSeconds, setSimulationSeconds] = useState(
    String(user.custom_simulation_seconds ?? ""),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await updateUser(user.id, {
        name: name.trim() || null,
        exam_code: examCode.trim() || null,
        exam_date: examDate || null,
        needs_extra_time: extraTime,
        custom_reading_seconds: secondsOrNull(readingSeconds),
        custom_simulation_seconds: secondsOrNull(simulationSeconds),
      });
      onSaved(updated);
      toast.success("Profile saved");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [
    user.id,
    name,
    examCode,
    examDate,
    extraTime,
    readingSeconds,
    simulationSeconds,
    onSaved,
    toast,
  ]);

  return (
    <Panel title="Profile">
      <div className="flex max-w-lg flex-col gap-4">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <Input
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={busy}
        />
        <AsyncBoundary state={exams} isEmpty={() => false}>
          {(page) => (
            <Select
              label="Exam"
              value={examCode}
              onChange={(e) => setExamCode(e.target.value)}
              disabled={busy}
              hint="The exam this person is preparing for. What they can use is on the Access and billing tab."
            >
              <option value="">No exam chosen</option>
              {page.items.map((exam) => (
                <option key={exam.code} value={exam.code}>
                  {exam.name} ({exam.code.toUpperCase()})
                </option>
              ))}
              {examCode &&
              !page.items.some((exam) => exam.code === examCode) ? (
                <option value={examCode}>
                  {examCode} (not in the catalogue)
                </option>
              ) : null}
            </Select>
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

        <div className="flex flex-col gap-4 border-t border-border pt-4">
          <Checkbox
            label="Extra time"
            description="Uses the custom timers below on their own practice."
            checked={extraTime}
            onChange={(e) => setExtraTime(e.target.checked)}
            disabled={busy}
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              type="number"
              min={1}
              max={3659}
              inputMode="numeric"
              label="Reading (seconds)"
              value={readingSeconds}
              onChange={(e) => setReadingSeconds(e.target.value)}
              disabled={busy}
              hint="Blank keeps the exam's own."
            />
            <Input
              type="number"
              min={1}
              max={3659}
              inputMode="numeric"
              label="Consultation (seconds)"
              value={simulationSeconds}
              onChange={(e) => setSimulationSeconds(e.target.value)}
              disabled={busy}
              hint="Blank keeps the exam's own."
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button disabled={busy} onClick={() => save()}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </Panel>
  );
}

function PasswordReset({ userId }: { userId: string }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = async () => {
    setBusy(true);
    setError(null);
    try {
      await resetUserPassword(userId);
      toast.success(
        "Password reset emailed",
        "A link to choose a new password is on its way to them.",
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ActionRail title="Sign-in">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <Button variant="secondary" disabled={busy} onClick={() => reset()}>
        {busy ? "Sending…" : "Send password reset"}
      </Button>
    </ActionRail>
  );
}

/** A typed number of seconds, or `null` for a blank field (the exam's own length). */
function secondsOrNull(value: string): number | null {
  const seconds = Number.parseInt(value, 10);
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
}
