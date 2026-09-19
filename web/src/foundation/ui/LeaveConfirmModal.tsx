import ConfirmModal from "@/foundation/ui/ConfirmModal";

interface LeaveConfirmModalProps {
  isOpen: boolean;
  onStay: () => void;
  onLeave: () => void;
  title?: string;
  message?: string;
  leaveText?: string;
  stayText?: string;
  isLeaving?: boolean;
}

/** Wraps ConfirmModal with the unsaved-changes / exit-guard defaults. */
export default function LeaveConfirmModal({
  isOpen,
  onStay,
  onLeave,
  title = "Leave without saving?",
  message = "You have unsaved changes. If you leave now they will be lost.",
  leaveText = "Leave",
  stayText = "Stay",
  isLeaving = false,
}: LeaveConfirmModalProps) {
  return (
    <ConfirmModal
      isOpen={isOpen}
      onCancel={onStay}
      onConfirm={onLeave}
      title={title}
      message={message}
      confirmText={leaveText}
      cancelText={stayText}
      tone="danger"
      isLoading={isLeaving}
    />
  );
}
