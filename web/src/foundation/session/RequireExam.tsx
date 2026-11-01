"use client";

import { Fragment, type ReactNode } from "react";
import { Alert, Button, Spinner } from "@/foundation/ui";
import { classifyExam } from "@/foundation/session/examCode";
import { useCurrentExam } from "@/foundation/session/useCurrentExam";

/**
 * The outer half of a screen that asks the api about the person's exam: a spinner while the
 * dashboard answers, an explanation with "Try again" when no exam is named, and otherwise the
 * inner screen, handed an `examCode` that is always a real one (see `classifyExam`). The inner
 * screen is keyed by the code, so a changed exam remounts it rather than keeping its state.
 */
export function RequireExam({ children }: { children: (examCode: string) => ReactNode }) {
  const { code, loading, error, reload } = useCurrentExam();
  const exam = classifyExam({ code, loading, error });
  if (exam.kind === "loading") return <Spinner size="sm" label="Loading your exam" />;
  if (exam.kind === "unknown") {
    return (
      <Alert tone="info" title="We don't know your exam yet">
        <p>
          We could not tell which exam you are practising for, so we have not started anything. Try again, and
          contact us if this stays.
        </p>
        <Button type="button" variant="secondary" size="sm" className="mt-3" onClick={reload}>
          Try again
        </Button>
      </Alert>
    );
  }
  return <Fragment key={exam.code}>{children(exam.code)}</Fragment>;
}
