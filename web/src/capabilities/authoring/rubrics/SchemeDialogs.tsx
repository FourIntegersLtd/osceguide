"use client";

import { ConfirmModal, LeaveConfirmModal } from "@/foundation/ui";
import type { RubricVersion } from "@/capabilities/authoring/api";
import type { OlderPublished } from "@/capabilities/authoring/rubrics/versionRows";

/** The scheme builder's confirmations: publish, archive, "a draft already exists", and leaving with unsaved changes. */
export function SchemeDialogs({
  version,
  older,
  publishing,
  onPublishCancel,
  onPublish,
  archiving,
  onArchiveCancel,
  onArchive,
  draftExists,
  openDraftVersion,
  onDraftExistsClose,
  leaving,
  onStay,
  onLeave,
}: {
  version: RubricVersion;
  older: OlderPublished | null;
  publishing: boolean;
  onPublishCancel: () => void;
  onPublish: () => void;
  archiving: RubricVersion | null;
  onArchiveCancel: () => void;
  onArchive: (target: RubricVersion) => void;
  draftExists: boolean;
  openDraftVersion: number | undefined;
  onDraftExistsClose: () => void;
  leaving: boolean;
  onStay: () => void;
  onLeave: () => void;
}) {
  return (
    <>
      <ConfirmModal
        isOpen={publishing}
        onCancel={onPublishCancel}
        onConfirm={onPublish}
        title={`Publish version ${version.version}?`}
        message={`Once published it cannot be changed. Sittings already marked keep the version they used.${older ? ` ${older.names} ${older.single ? "keeps" : "keep"} marking with version ${older.version} until you point ${older.single ? "it" : "them"} at version ${version.version}.` : ""}`}
        confirmText={`Publish version ${version.version}`}
      />
      <ConfirmModal
        isOpen={archiving !== null}
        onCancel={onArchiveCancel}
        onConfirm={() => archiving && onArchive(archiving)}
        title={`Archive version ${archiving?.version ?? ""}?`}
        message={`${archiving?.used_by_exams?.length ? `Exams use it: ${archiving.used_by_exams.join(", ")}, so it may be refused.` : "No exam uses it."} Archived versions stay readable and keep every result marked with them, but cannot be picked for an exam.`}
        confirmText={`Archive version ${archiving?.version ?? ""}`}
        tone="danger"
      />
      <ConfirmModal
        isOpen={draftExists}
        onCancel={onDraftExistsClose}
        onConfirm={onDraftExistsClose}
        title="A draft already exists"
        message={`Version ${openDraftVersion ?? ""} is the draft ${openDraftVersion === version.version ? "you are editing" : "in progress"}. Publish or discard it before starting another draft from an older version.`}
        confirmText="OK"
        cancelButton={false}
      />
      <LeaveConfirmModal message="Your changes to this draft since the last save will be lost." isOpen={leaving} onStay={onStay} onLeave={onLeave} />
    </>
  );
}
