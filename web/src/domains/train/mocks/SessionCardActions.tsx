"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlinePencilSquare, HiOutlineTrash } from "react-icons/hi2";
import { ConfirmModal, cn, productTokens } from "@/foundation/ui";
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

  const handleConfirmDelete = async () => {
    try {
      await deleteSet(set.id);
      setShowDeleteConfirmation(false);
      toast.success("Session deleted", `${set.name} has been removed.`);
      onChanged();
    } catch (cause) {
      toast.error("We couldn't delete this session", errorMessage(cause));
    }
  };

  return (
    <div className="relative z-10 flex shrink-0">
      <div className="flex opacity-100 transition-opacity md:opacity-0 md:group-focus-within:opacity-100 md:group-hover:opacity-100">
        <button
          type="button"
          aria-label={`Edit ${set.name}`}
          onClick={() => router.push(hrefFor(`/mocks/${set.id}/update`))}
          className={cn(productTokens.b2cIconButton, "sm:h-8 sm:w-8")}
        >
          <HiOutlinePencilSquare className="h-4 w-4" />
        </button>
        <button
          type="button"
          aria-label={`Delete ${set.name}`}
          onClick={() => setShowDeleteConfirmation(true)}
          className={cn(productTokens.b2cIconButton, "hover:text-osce-danger sm:h-8 sm:w-8")}
        >
          <HiOutlineTrash className="h-4 w-4" />
        </button>
      </div>

      <ConfirmModal
        isOpen={showDeleteConfirmation}
        tone="danger"
        title="Delete this session?"
        message={`${set.name} will be removed. This cannot be undone.`}
        confirmText="Delete"
        onCancel={() => setShowDeleteConfirmation(false)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
