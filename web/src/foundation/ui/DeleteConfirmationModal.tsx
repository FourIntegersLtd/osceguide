"use client";

import {
  HiOutlineArrowPath,
  HiOutlineCheckCircle,
  HiOutlineExclamationTriangle,
  HiOutlineTrash,
} from "react-icons/hi2";
import React from "react";
import Modal from "@/foundation/ui/Modal";
import {
  ModalContent,
  ModalDangerButton,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
} from "@/foundation/ui/ModalContent";

export type DeleteConfirmationModalPropType = {
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  setDeletionStatus: (status: boolean | null) => void;
  setLoading: (loading: boolean) => void;
  selectedName: string;
  deletionStatus: boolean | null;
  loading: boolean;
};

const DeleteConfirmationModal = ({
  isOpen,
  onCancel,
  onConfirm,
  selectedName,
  deletionStatus,
  loading,
}: DeleteConfirmationModalPropType) => {
  if (!isOpen) return null;

  return (
    <Modal
      onClose={onCancel}
      width="28rem"
      height="fit-content"
      hideCloseButton
    >
      <ModalContent>
        {loading ? (
          <ModalLead
            title="Deleting…"
            description={`Removing ${selectedName}.`}
            icon={<HiOutlineArrowPath className="h-5 w-5 animate-spin" />}
          />
        ) : deletionStatus === true ? (
          <>
            <ModalLead
              title="Deleted"
              description={`Successfully deleted ${selectedName}.`}
              icon={<HiOutlineCheckCircle className="h-5 w-5" />}
              iconTone="competent"
            />
            <ModalFooterActions>
              <ModalSecondaryButton onClick={onCancel}>
                Close
              </ModalSecondaryButton>
            </ModalFooterActions>
          </>
        ) : deletionStatus === false ? (
          <>
            <ModalLead
              title="Couldn't delete"
              description={`Something went wrong deleting ${selectedName}. Please try again.`}
              icon={<HiOutlineExclamationTriangle className="h-5 w-5" />}
              iconTone="rose"
            />
            <ModalFooterActions>
              <ModalSecondaryButton onClick={onCancel}>
                Cancel
              </ModalSecondaryButton>
              <ModalPrimaryButton onClick={onConfirm}>Retry</ModalPrimaryButton>
            </ModalFooterActions>
          </>
        ) : (
          <>
            <ModalLead
              title="Confirm deletion"
              description={
                <>
                  Are you sure you want to delete{" "}
                  <span className="break-words font-medium text-osce-ink-900">
                    {selectedName}
                  </span>
                  ? This action cannot be undone.
                </>
              }
              icon={<HiOutlineTrash className="h-5 w-5" />}
              iconTone="rose"
            />
            <ModalFooterActions>
              <ModalSecondaryButton onClick={onCancel}>
                Cancel
              </ModalSecondaryButton>
              <ModalDangerButton onClick={onConfirm}>Delete</ModalDangerButton>
            </ModalFooterActions>
          </>
        )}
      </ModalContent>
    </Modal>
  );
};

export default DeleteConfirmationModal;