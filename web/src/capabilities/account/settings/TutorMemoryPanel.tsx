"use client";

import { useState } from "react";
import { HiOutlineClock, HiOutlinePencilSquare, HiOutlineTrash } from "react-icons/hi2";
import { AsyncBoundary, Button, Checkbox, ConfirmModal, Panel } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  forgetTutorMemory,
  forgetTutorNote,
  readTutorMemory,
  type TutorMemory,
  type TutorNote,
} from "@/capabilities/account/api";
import { SettingsRow, SettingsRows, SettingsSection } from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import { noteSentence } from "@/capabilities/account/settings/tutorNotes";

const SHORT_DATE: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };

/** Recent activity shows this many until "Show all"; the newest come first. */
const RECENT_EVENTS = 5;

/**
 * What the tutor remembers about you, and the way to delete it.
 *
 * A memory nobody can inspect is one nobody can correct, and Athena speaks
 * from this every time she opens her mouth. The screen is a list rather than a
 * summary for that reason: a person disputing what the tutor said about them
 * needs the individual note, and a note is deletable on its own.
 */
export default function TutorMemoryPanel() {
  const memory = useAsync((signal) => readTutorMemory(signal), []);
  const toast = useToast();
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
      toast.success("Athena's notes are deleted");
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
            <Panel
              title="Memory"
              description="Athena keeps a few short notes from your consultations and debriefs so she can pick up where you left off. Nothing else is recorded, and you can delete any note here."
              padding="none"
              actions={
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setConfirmForget(true)}
                  disabled={
                    data.notes.length === 0 &&
                    data.events.length === 0 &&
                    data.debrief_summaries.length === 0
                  }
                >
                  Delete all notes
                </Button>
              }
            >
              {data.notes.length === 0 ? (
                <p className="p-4 text-osce-body text-ink-muted">
                  No notes yet. Athena starts after your first consultation.
                </p>
              ) : (
                <div className="[&>*+*]:border-t [&>*+*]:border-osce-border-light">
                  {data.notes.map((note) => (
                    <NoteRow
                      key={note.id}
                      note={note}
                      onDeleted={() => {
                        toast.success("Note deleted");
                        memory.reload();
                      }}
                    />
                  ))}
                </div>
              )}
            </Panel>

            <ActivityCard memory={data} />
          </>
        )}
      </AsyncBoundary>

      <ConfirmModal
        isOpen={confirmForget}
        onCancel={() => setConfirmForget(false)}
        onConfirm={() => handleForgetAll()}
        title="Delete everything Athena remembers?"
        message="She loses every note and every event she has about you. Your attempts, your feedback and your results are untouched."
        confirmText="Delete everything"
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

function NoteRow({ note, onDeleted }: { note: TutorNote; onDeleted: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    setError(null);
    setBusy(true);
    try {
      await forgetTutorNote(note.id);
      onDeleted();
    } catch (cause) {
      setError(errorMessage(cause));
      setBusy(false);
    }
  };

  return (
    <SettingsRow
      icon={HiOutlinePencilSquare}
      title={noteSentence(note)}
      meta={
        <>
          <span className="capitalize">{note.kind.replace(/_/g, " ")}</span> ·{" "}
          {new Date(note.created_at).toLocaleDateString("en-GB", SHORT_DATE)}
        </>
      }
      trailing={
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => handleDelete()} isLoading={busy}>
          <HiOutlineTrash className="h-4 w-4" aria-hidden />
          Delete
        </Button>
      }
    >
      {error ? <p className="mt-1 text-osce-meta text-danger">{error}</p> : null}
    </SettingsRow>
  );
}

function ActivityCard({ memory }: { memory: TutorMemory }) {
  const [showAll, setShowAll] = useState(false);
  if (memory.events.length === 0) return null;
  const shown = showAll ? memory.events : memory.events.slice(0, RECENT_EVENTS);
  return (
    <SettingsSection
      eyebrow={
        <>
          Recent activity
          <span className="block font-normal text-ink-subtle">
            Which stations and debriefs you opened. Used only to suggest what to practise next.
          </span>
        </>
      }
    >
      <SettingsRows>
        {shown.map((event) => (
          <SettingsRow
            key={event.id}
            icon={HiOutlineClock}
            title={event.title}
            meta={new Date(event.occurred_at).toLocaleDateString("en-GB", SHORT_DATE)}
          />
        ))}
      </SettingsRows>
      {memory.events.length > RECENT_EVENTS && !showAll ? (
        <Button variant="ghost" size="sm" className="mt-2" onClick={() => setShowAll(true)}>
          Show all ({memory.events.length})
        </Button>
      ) : null}
    </SettingsSection>
  );
}
