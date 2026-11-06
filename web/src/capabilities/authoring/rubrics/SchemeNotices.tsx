"use client";

import { Alert } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import type { OlderPublished } from "@/capabilities/authoring/rubrics/versionRows";

/** Every banner above the tabs: conflict, errors, notes, read-only, blocked publish, published, unapplied JSON. */
export function SchemeNotices({
  conflict,
  onStale,
  error,
  note,
  checkError,
  readOnly,
  owned,
  version,
  status,
  exams,
  starting,
  onNewDraft,
  problemCount,
  blocked,
  onSeeProblems,
  published,
  older,
  onOpenExam,
  jsonPending,
  onOpenJson,
}: {
  conflict: boolean;
  onStale: () => void;
  error: string | null;
  note: string | null;
  checkError: string | null;
  readOnly: boolean;
  owned: boolean;
  version: number;
  status: string;
  /** The exams that mark with this version. */
  exams: readonly string[];
  starting: boolean;
  onNewDraft: () => void;
  problemCount: number;
  /** Publishing is not offered right now. */
  blocked: boolean;
  onSeeProblems: () => void;
  published: boolean;
  older: OlderPublished | null;
  onOpenExam: () => void;
  jsonPending: boolean;
  onOpenJson: () => void;
}) {
  return (
    <>
      {conflict ? (
        <Alert tone="danger">
          This draft was saved somewhere else while you were editing, so your save was refused. Reload the latest draft, then make your change again.{" "}
          <AuthoringButton variant="ghost" size="sm" onClick={onStale}>Reload latest</AuthoringButton>
        </Alert>
      ) : null}
      {error && !conflict ? <Alert tone="danger">{error}</Alert> : null}
      {note ? <Alert tone="info">{note}</Alert> : null}
      {checkError ? <Alert tone="warning">The draft could not be checked: {checkError}</Alert> : null}
      {jsonPending && !readOnly ? (
        <Alert tone="warning">
          You have JSON edits that are not applied, so Save is off. Apply or discard them first.{" "}
          <AuthoringButton variant="ghost" size="sm" onClick={onOpenJson}>Open the JSON</AuthoringButton>
        </Alert>
      ) : null}
      {readOnly && !published ? (
        <Alert tone="info">
          {owned
            ? `Version ${version} is ${status === "archived" ? "archived" : "published"}, so it cannot be changed.${exams.length ? ` ${exams.join(", ")} marks with it.` : ""} To change it, start a new draft from it.`
            : "This version is read-only. Start a new draft to change it."}{" "}
          {owned ? (
            <AuthoringButton variant="ghost" size="sm" isLoading={starting} onClick={onNewDraft}>
              New draft from version {version}
            </AuthoringButton>
          ) : null}
        </Alert>
      ) : null}
      {!readOnly && blocked && problemCount > 0 ? (
        <Alert tone="warning">
          Publishing is blocked: {problemCount} {problemCount === 1 ? "problem" : "problems"} to fix.{" "}
          <AuthoringButton variant="ghost" size="sm" onClick={onSeeProblems}>See problems</AuthoringButton>
        </Alert>
      ) : null}
      {published ? (
        <Alert tone="info">
          {older
            ? `Version ${version} is published. ${older.names} still ${older.single ? "marks" : "mark"} with version ${older.version} until you point ${older.single ? "it" : "them"} at version ${version}.`
            : `Version ${version} is published. Point an exam at it to mark with it.`}{" "}
          <AuthoringButton variant="ghost" size="sm" onClick={onOpenExam}>Open the exam</AuthoringButton>
        </Alert>
      ) : null}
    </>
  );
}
