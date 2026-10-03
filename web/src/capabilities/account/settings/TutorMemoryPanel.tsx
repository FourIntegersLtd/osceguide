"use client";

import { useState } from "react";
import { HiOutlineTrash } from "react-icons/hi2";
import {
  AsyncBoundary,
  Button,
  Checkbox,
  ConfirmModal,
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
import { B2CHero } from "@/foundation/ui/B2CHero";

const { b2cMonoEyebrow } = productTokens;

const ROW_LIST =
  "divide-y divide-border overflow-hidden rounded-osce-lg border border-border bg-surface";

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
    <SettingsTabShell>
      <AsyncBoundary state={memory}>
        {(data: TutorMemory) => (
          <>
            <B2CHero
              eyebrow="What Athena remembers"
              title="Athena keeps notes so she can pick up where you left off"
              action={
                <Button
                  type="button"
                  variant="secondary"
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
                </Button>
              }
            >
              From your consultations and debriefs. Forget any note, or all of them.
            </B2CHero>

            <section>
              <p className={`mb-2 ${b2cMonoEyebrow}`}>Notes</p>
              {data.notes.length === 0 ? (
                <p className="rounded-osce-lg border border-dashed border-border p-4 text-osce-body text-ink-subtle">
                  Athena has not made any notes yet. She starts after your first consultation.
                </p>
              ) : (
                <ul className={ROW_LIST}>
                  {data.notes.map((note) => (
                    <NoteRow key={note.id} note={note} onForgotten={memory.reload} />
                  ))}
                </ul>
              )}
            </section>

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
        <Checkbox
          className="text-left"
          checked={includeDebriefs}
          onChange={(event) => setIncludeDebriefs(event.target.checked)}
          label="Also delete my debrief summaries. These appear on your own results as well, and deleting them removes them from there too."
        />
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
    <li className="flex min-h-[54px] items-center gap-3 px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <p className="text-osce-body font-medium text-ink">{noteSentence(note)}</p>
        <p className="text-osce-meta text-ink-subtle">
          <span className="capitalize">{note.kind.replace(/_/g, " ")}</span> ·{" "}
          {new Date(note.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
        </p>
        {error ? <p className="mt-1 text-osce-meta text-osce-danger">{error}</p> : null}
      </div>
      <Button type="button" variant="ghost" size="sm" onClick={() => void handleForget()} isLoading={busy} className="shrink-0">
        Forget this note
      </Button>
    </li>
  );
}

function ActivityCard({ memory }: { memory: TutorMemory }) {
  if (memory.events.length === 0) return null;
  return (
    <section>
      <p className={`mb-2 ${b2cMonoEyebrow}`}>What she has seen you do</p>
      <ul className={ROW_LIST}>
        {memory.events.map((event) => (
          <li key={event.id} className="flex min-h-[54px] items-center justify-between gap-3 px-4 py-2.5">
            <span className="min-w-0 truncate text-osce-body text-ink">{event.title}</span>
            <span className="shrink-0 text-osce-meta text-ink-subtle">
              {new Date(event.occurred_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
