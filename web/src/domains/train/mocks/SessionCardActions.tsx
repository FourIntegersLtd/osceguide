"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlinePencilSquare, HiOutlineTrash } from "react-icons/hi2";
import { DeleteConfirmationModal } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { deleteSet, type StationSet } from "@/domains/train/api";

/**
 * The pencil and the bin on one session card, as the retiring `MockList` drew
 * them: the pencil goes to the session's update page, the bin asks first.
 *
 * The bin is the one control that can be refused. A set somebody has started a
 * station in answers 409 `set_has_attempts` rather than have the ground taken
 * out from under those recordings; like any other failure it is the old
 * "We couldn't delete this session" toast with the server's sentence.
 */
export function SessionCardActions({
  set,
  onChanged,
}: {
  set: StationSet;
  /** The list's own reload, so a write is followed by the server's answer. */
  onChanged: () => void;
}) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const toast = useToast();
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [deletionStatus, setDeletionStatus] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleConfirmDelete = async () => {
    setIsLoading(true);
    try {
      await deleteSet(set.id);
      setDeletionStatus(true);
      setShowDeleteConfirmation(false);
      toast.success("Session deleted", `${set.name} has been removed.`);
      onChanged();
    } catch (cause) {
      setDeletionStatus(false);
      toast.error("We couldn't delete this session", errorMessage(cause));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="absolute top-2 right-2 z-20 flex gap-2">
      <div>
        <button
          type="button"
          aria-label={`Edit ${set.name}`}
          onClick={() => router.push(hrefFor(`/mocks/${set.id}/update`))}
          className="rounded-md bg-osce-surface/80 p-2 backdrop-blur transition-all duration-300 hover:bg-osce-surface"
        >
          <HiOutlinePencilSquare className="text-osce-subheading text-b2c-text-muted transition-all duration-300 hover:scale-110 hover:text-osce-accent" />
        </button>
        <button
          type="button"
          aria-label={`Delete ${set.name}`}
          onClick={() => {
            setDeletionStatus(null);
            setShowDeleteConfirmation(true);
          }}
          className="rounded-md bg-osce-surface/80 p-2 backdrop-blur transition-all duration-300 hover:bg-osce-surface"
        >
          <HiOutlineTrash className="text-osce-subheading text-b2c-text-muted transition-all duration-300 hover:scale-110 hover:text-osce-danger" />
        </button>
      </div>

      {showDeleteConfirmation && (
        <DeleteConfirmationModal
          isOpen={showDeleteConfirmation}
          onCancel={() => {
            setShowDeleteConfirmation(false);
            setDeletionStatus(null);
          }}
          onConfirm={() => void handleConfirmDelete()}
          setDeletionStatus={setDeletionStatus}
          setLoading={setIsLoading}
          deletionStatus={deletionStatus}
          selectedName={set.name}
          loading={isLoading}
        />
      )}
    </div>
  );
}
