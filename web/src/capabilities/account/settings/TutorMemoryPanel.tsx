"use client";

import { useState } from "react";
import { HiOutlineClock, HiOutlineSparkles, HiOutlineTrash } from "react-icons/hi2";
import {
  AsyncBoundary,
  AthenaIdentity,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ConfirmModal,
  ModalDangerButton,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  forgetTutorMemory,
  forgetTutorNote,
  readTutorMemory,
  type TutorMemory,
  type TutorNote,
} from "@/capabilities/account/api";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import { noteSentence } from "@/capabilities/account/settings/tutorNotes";

const { b2cFieldLabel, b2cSettingsCardHeaderIcon } = productTokens;

/**
 * What the tutor remembers about you, and the way to make it forget.
 *
 * A memory nobody can inspect is one nobody can correct, and Athena speaks
 * from this every time she opens her mouth. The screen is a list rather than a
 * summary for that reason: a person disputing what the tutor said about them
 * needs the individual note, and a note is deletable on its own.
 */
export default function TutorMemoryPanel() {
  const memory = useAsync((signal) => readTutorMemory(signal), []);
  const [confirmForget, setConfirmForget] = useState(false);
  const [includeDebriefs, setIncludeDebriefs] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleForgetAll = async () => {
    setError(null);
    setBusy(true);
    try {
      await forgetTutorMemory(includeDebriefs);
      setConfirmForget(false);
      memory.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SettingsTabShell fullWidth>
      <AsyncBoundary state={memory}>
        {(data: TutorMemory) => (
          <>
            <B2CPanelCard className="mt-0">
              <B2CPanelCardHeader>
                <HiOutlineSparkles className={b2cSettingsCardHeaderIcon} aria-hidden />
                What Athena remembers
              </B2CPanelCardHeader>
              <B2CPanelCardBody className="space-y-4">
                <AthenaIdentity
                  layout="inline"
                  description="Athena keeps notes from your consultations and debriefs so she can pick up where you left off. Everything she holds is here, and you can make her forget any of it."
                />

                {data.notes.length === 0 ? (
                  <p className="rounded-md bg-b2c-surface-muted p-3 text-osce-body italic text-b2c-text-muted sm:p-4">
                    Athena has not made any notes yet. She starts after your first
                    consultation.
                  </p>
                ) : (
                  <ul className="divide-y divide-b2c-border rounded-xl border border-b2c-border">
                    {data.notes.map((note) => (
                      <NoteRow key={note.id} note={note} onForgotten={memory.reload} />
                    ))}
                  </ul>
                )}
              </B2CPanelCardBody>
              <B2CPanelCardFooter>
                <ModalDangerButton
                  type="button"
                  onClick={() => setConfirmForget(true)}
                  disabled={
                    data.notes.length === 0 &&
                    data.events.length === 0 &&
                    data.debrief_summaries.length === 0
                  }
                  className="gap-2"
                >
                  <HiOutlineTrash className="h-4 w-4" aria-hidden />
                  Forget everything
                </ModalDangerButton>
              </B2CPanelCardFooter>
            </B2CPanelCard>

            <ActivityCard memory={data} />
          </>
        )}
      </AsyncBoundary>

      <ConfirmModal
        isOpen={confirmForget}
        onCancel={() => setConfirmForget(false)}
        onConfirm={() => void handleForgetAll()}
        title="Make Athena forget?"
        message="She loses every note and every event she has about you. Your attempts, your feedback and your results are untouched."
        confirmText="Forget it all"
        cancelText="Keep it"
        tone="danger"
        isLoading={busy}
        error={error}
      >
        {/*
          Debrief summaries are opt-in on the way out: they are also this
          doctor's own record of what a debrief concluded, shown on their
          results, so clearing the tutor's memory does not delete them unless
          asked.
        */}
        <label className="flex items-start gap-3 text-left">
          <input
            type="checkbox"
            checked={includeDebriefs}
            onChange={(event) => setIncludeDebriefs(event.target.checked)}
            className="mt-1 h-4 w-4 shrink-0 rounded border-b2c-border text-osce-accent focus:ring-osce-accent/20"
          />
          <span className="text-osce-meta text-b2c-text-muted">
            Also delete my debrief summaries. These appear on your own results as well,
            and deleting them removes them from there too.
          </span>
        </label>
      </ConfirmModal>
    </SettingsTabShell>
  );
}

function NoteRow({ note, onForgotten }: { note: TutorNote; onForgotten: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleForget = async () => {
    setError(null);
    setBusy(true);
    try {
      await forgetTutorNote(note.id);
      onForgotten();
    } catch (cause) {
      setError(errorMessage(cause));
      setBusy(false);
    }
  };

  return (
    <li className="flex items-start justify-between gap-4 px-4 py-3">
      <div className="min-w-0">
        <p className="text-osce-meta capitalize text-b2c-text-muted">
          {note.kind.replace(/_/g, " ")}
        </p>
        <p className="text-osce-body text-osce-ink-900">{noteSentence(note)}</p>
        <p className={b2cFieldLabel}>{new Date(note.created_at).toLocaleDateString()}</p>
        {error ? <p className="mt-1 text-osce-meta text-osce-danger">{error}</p> : null}
      </div>
      <button
        type="button"
        onClick={() => void handleForget()}
        disabled={busy}
        aria-label="Forget this note"
        className="shrink-0 rounded-md p-1.5 text-b2c-text-muted transition-colors hover:bg-osce-surface hover:text-osce-danger disabled:opacity-50"
      >
        <HiOutlineTrash className="h-4 w-4" aria-hidden />
      </button>
    </li>
  );
}

function ActivityCard({ memory }: { memory: TutorMemory }) {
  if (memory.events.length === 0) return null;
  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>
        <HiOutlineClock className={b2cSettingsCardHeaderIcon} aria-hidden />
        What she has seen you do
      </B2CPanelCardHeader>
      <B2CPanelCardBody>
        <ul className="divide-y divide-b2c-border rounded-xl border border-b2c-border">
          {memory.events.map((event) => (
            <li
              key={event.id}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
            >
              <span className="min-w-0 truncate text-osce-body text-osce-ink-900">
                {event.title}
              </span>
              <span className="shrink-0 text-osce-meta text-b2c-text-muted">
                {new Date(event.occurred_at).toLocaleDateString()}
              </span>
            </li>
          ))}
        </ul>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}
