"use client";

import { useState } from "react";
import { HiOutlineAcademicCap, HiOutlineArrowPath } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  Button,
  ModalHelper,
  cn,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { useCurrentExam, useSession } from "@/foundation/session";
import { rememberExamSelection } from "@/foundation/session/examSelection";
import { updateMe } from "@/capabilities/account/api";
import { listExams, type Exam } from "@/capabilities/stations/api";

const { b2cSettingsCardHeaderIcon } = productTokens;

/**
 * "Which exam are you sitting?" — asked once, of an account that has none.
 *
 * Sign-up records the exam only when the visitor came through an exam's own
 * landing page; the form cannot offer a choice, because the catalogue needs a
 * token and the form is the screen before there is one. Everybody else used
 * to open an app that was about no exam in particular, and a payments tab that
 * sold them all of them. So the consumer shell shows this instead of the app
 * until the answer is stored.
 *
 * The backend accepts the answer only while the account has no exam
 * (`identity/service.py`, `_exam_to_set`): after that, switching is a support
 * action, as the Exam tab says.
 */
export default function ChooseExam() {
  const exams = useAsync((signal) => listExams(signal), []);

  return (
    <div className="flex min-h-dvh items-center justify-center bg-b2c-surface-muted px-4 py-10">
      <B2CPanelCard className="mt-0 w-full max-w-lg overflow-hidden">
        <B2CPanelCardHeader>
          <HiOutlineAcademicCap className={b2cSettingsCardHeaderIcon} aria-hidden />
          Which exam are you sitting?
        </B2CPanelCardHeader>
        <B2CPanelCardBody>
          <AsyncBoundary state={exams}>
            {(page) => (
              // A platform admin's catalogue includes drafts, which nobody can
              // be on: the backend refuses them as `unknown_exam`.
              <ExamChoice exams={page.items.filter((exam) => exam.status === "published")} />
            )}
          </AsyncBoundary>
        </B2CPanelCardBody>
      </B2CPanelCard>
    </div>
  );
}

function ExamChoice({ exams }: { exams: Exam[] }) {
  const { session, refresh } = useSession();
  // Somebody who bought an exam before this step existed holds it already;
  // start them on it rather than on whichever exam sorts first.
  const { codes: heldCodes } = useCurrentExam();
  const [picked, setPicked] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = picked ?? heldCodes.find((code) => exams.some((exam) => exam.code === code)) ?? null;

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      await updateMe({ exam_code: selected });
      if (session) rememberExamSelection(session.user.id, selected);
      // The shell re-reads the account and, with an exam on it, opens the app.
      await refresh();
    } catch (cause) {
      if (hasCode(cause, "exam_already_chosen")) {
        // Set elsewhere in the meantime (another tab, or support): that answer
        // stands, and re-reading the account moves them on to it.
        await refresh();
        return;
      }
      setError(errorMessage(cause));
      setSaving(false);
    }
  };

  return (
    <div>
      <ModalHelper className="mb-5 mt-0">
        It decides your stations, study material and practice partners. You can change it later
        only by contacting support.
      </ModalHelper>

      <div className="-mx-3 divide-y divide-b2c-border sm:-mx-4" role="radiogroup" aria-label="Exam">
        {exams.map((exam) => {
          const isSelected = selected === exam.code;
          return (
            <button
              key={exam.code}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => setPicked(exam.code)}
              className={cn(
                "flex w-full flex-col items-start gap-0.5 px-3 py-4 text-left transition sm:px-4",
                isSelected
                  ? "bg-osce-accent-muted hover:bg-osce-accent-subtle"
                  : "hover:bg-b2c-surface-muted",
              )}
            >
              <span
                className={cn(
                  "text-osce-body font-medium",
                  isSelected ? "text-osce-accent-hover" : "text-osce-ink-900",
                )}
              >
                {exam.code.toUpperCase()}
              </span>
              {exam.name.toUpperCase() !== exam.code.toUpperCase() ? (
                <span className="text-osce-meta text-b2c-text-muted">{exam.name}</span>
              ) : null}
            </button>
          );
        })}
      </div>

      {error ? <p className="mt-4 text-osce-meta text-osce-danger">{error}</p> : null}

      <div className="mt-6 flex sm:justify-end">
        <Button
          type="button"
          variant="primary"
          size="md"
          onClick={() => void save()}
          disabled={saving || !selected}
          className="inline-flex w-full items-center justify-center gap-2 sm:w-auto"
        >
          {saving ? (
            <>
              <HiOutlineArrowPath className="h-4 w-4 shrink-0 animate-spin" aria-hidden />
              Saving...
            </>
          ) : (
            "Continue"
          )}
        </Button>
      </div>
    </div>
  );
}
