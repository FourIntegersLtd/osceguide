"use client";

import { useState } from "react";
import { HiOutlineCalendarDays } from "react-icons/hi2";
import {
  Input,
  Modal,
  ModalContent,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalSection,
} from "@/foundation/ui";
import {
  EARLIEST_DATE,
  utcDateString,
  validateCustomRange,
} from "@/capabilities/attribution-dashboard/presets";

interface CustomDateRangeModalProps {
  open: boolean;
  fromDate: string;
  toDate: string;
  onClose: () => void;
  onApply: (range: { fromDate: string; toDate: string }) => void;
}

/** Two date inputs and the four ways a range can be wrong, said before the request is made. */
export function CustomDateRangeModal({
  open,
  fromDate,
  toDate,
  onClose,
  onApply,
}: CustomDateRangeModalProps) {
  const [draftFrom, setDraftFrom] = useState(fromDate);
  const [draftTo, setDraftTo] = useState(toDate);
  const [error, setError] = useState<string | null>(null);

  // Reopening starts from the range now in force, not the last abandoned draft.
  const [previous, setPrevious] = useState({ open, fromDate, toDate });
  if (previous.open !== open || previous.fromDate !== fromDate || previous.toDate !== toDate) {
    setPrevious({ open, fromDate, toDate });
    if (open) {
      setDraftFrom(fromDate);
      setDraftTo(toDate);
      setError(null);
    }
  }

  if (!open) return null;

  const today = utcDateString(new Date());
  const apply = () => {
    const problem = validateCustomRange(draftFrom, draftTo);
    if (problem) {
      setError(problem);
      return;
    }
    onApply({ fromDate: draftFrom, toDate: draftTo });
    onClose();
  };

  return (
    <Modal width="min(95vw, 420px)" height="fit-content" onClose={onClose} title="Custom date range">
      <ModalContent>
        <ModalLead
          title="Custom date range"
          description="Choose the start and end dates for this report."
          icon={<HiOutlineCalendarDays className="h-5 w-5" />}
        />
        <ModalSection title="Date range">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input
              type="date"
              label="From"
              min={EARLIEST_DATE}
              max={today}
              value={draftFrom}
              onChange={(event) => {
                setDraftFrom(event.target.value);
                setError(null);
              }}
            />
            <Input
              type="date"
              label="To"
              min={EARLIEST_DATE}
              max={today}
              value={draftTo}
              onChange={(event) => {
                setDraftTo(event.target.value);
                setError(null);
              }}
            />
          </div>
        </ModalSection>
        {error ? (
          <p role="alert" className="text-osce-meta leading-relaxed text-osce-danger-text">
            {error}
          </p>
        ) : null}
        <ModalFooterActions>
          <ModalSecondaryButton type="button" onClick={onClose}>
            Cancel
          </ModalSecondaryButton>
          <ModalPrimaryButton type="button" onClick={apply}>
            Apply
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}
