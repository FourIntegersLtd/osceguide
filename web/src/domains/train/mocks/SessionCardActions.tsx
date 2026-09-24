"use client";

import { useState, type FormEvent } from "react";
import { HiOutlinePencilSquare, HiOutlineTrash } from "react-icons/hi2";
import { Alert, Button, ConfirmModal, Input, Modal } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { deleteSet, renameSet, type StationSet } from "@/domains/train/api";

/**
 * The pencil and the bin on one session card.
 *
 * Two writes the retiring client had and this screen did not: `MockList` drew
 * a trash icon beside every card, and `UpdateMock` was the page the pencil went
 * to. That page changed two things — the name and the list of stations — and
 * `PATCH /me/station-sets/{id}` changes the name on purpose. An entry carries
 * the counters for what was sat in it and is what an attempt points at, so
 * swapping the list is not an edit but a deletion, and this route would not
 * pretend otherwise. So the pencil opens the name field here rather than a
 * page, keeping the label and the button the old screen used.
 *
 * The bin is the one control that can be refused. A set somebody has started a
 * station in answers 409 `set_has_attempts` rather than have the ground taken
 * out from under those recordings, and this shows that sentence and stops: it
 * is a fact about the set, not a request that might land on the second try.
 */
export function SessionCardActions({
  set,
  onChanged,
}: {
  set: StationSet;
  /** The list's own reload, so a write is followed by the server's answer. */
  onChanged: () => void;
}) {
  const toast = useToast();
  const [renaming, setRenaming] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [name, setName] = useState(set.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openRename = () => {
    setName(set.name);
    setError(null);
    setRenaming(true);
  };

  const closeRename = () => {
    if (busy) return;
    setRenaming(false);
    setError(null);
  };

  const submitRename = async (event: FormEvent) => {
    event.preventDefault();
    const title = name.trim();
    if (title === "" || title === set.name) {
      setRenaming(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await renameSet(set.id, title);
      setRenaming(false);
      toast.success("Session has been updated successfully.");
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  const confirmDelete = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteSet(set.id);
      setConfirming(false);
      toast.success("Session deleted", `${set.name} has been removed.`);
      onChanged();
    } catch (cause) {
      if (hasCode(cause, "set_has_attempts")) {
        setConfirming(false);
        toast.error("This session can't be deleted", errorMessage(cause));
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="absolute right-2 top-2 z-20 flex gap-2">
      <button
        type="button"
        aria-label={`Edit ${set.name}`}
        onClick={openRename}
        className="rounded-md bg-osce-surface/80 p-2 backdrop-blur transition-all duration-300 hover:bg-osce-surface"
      >
        <HiOutlinePencilSquare
          className="text-osce-subheading text-b2c-text-muted transition-all duration-300 hover:scale-110 hover:text-osce-accent"
          aria-hidden
        />
      </button>
      <button
        type="button"
        aria-label={`Delete ${set.name}`}
        onClick={() => {
          setError(null);
          setConfirming(true);
        }}
        className="rounded-md bg-osce-surface/80 p-2 backdrop-blur transition-all duration-300 hover:bg-osce-surface"
      >
        <HiOutlineTrash
          className="text-osce-subheading text-b2c-text-muted transition-all duration-300 hover:scale-110 hover:text-osce-danger"
          aria-hidden
        />
      </button>

      {renaming ? (
        <Modal onClose={closeRename} title="Update session" width="min(32rem, 96vw)">
          <form onSubmit={submitRename} className="flex flex-col gap-3 p-4 lg:p-6">
            {error ? <Alert tone="danger">{error}</Alert> : null}

            <Input
              label="Give your session a name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Enter session name"
              autoComplete="off"
              disabled={busy}
              required
            />

            <div className="flex justify-end gap-2 pt-1">
              <Button type="button" variant="ghost" disabled={busy} onClick={closeRename}>
                Cancel
              </Button>
              <Button type="submit" disabled={busy || name.trim() === ""}>
                {busy ? "Updating..." : "Update session"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}

      <ConfirmModal
        isOpen={confirming}
        onCancel={() => {
          if (!busy) setConfirming(false);
        }}
        onConfirm={() => void confirmDelete()}
        isLoading={confirming && busy}
        error={error}
        tone="danger"
        title="Confirm deletion"
        confirmText="Delete"
        message={
          <>
            Are you sure you want to delete{" "}
            <span className="break-words font-medium text-osce-ink-900">{set.name}</span>? This
            action cannot be undone.
          </>
        }
      />
    </div>
  );
}
