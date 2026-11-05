"use client";

import { useState } from "react";
import { Modal, ModalContent, ModalSecondaryButton, ModalFooterActions, ModalTitle } from "@/foundation/ui";
import { TabStrip } from "@/domains/assess/team/chrome";
import { AddTraineePanel } from "@/domains/assess/roster/AddTraineePanel";
import { InvitePanel } from "@/domains/assess/team/InvitePanel";
import type { Cohort } from "@/domains/assess/roster/api";
import { useAssessWords } from "@/domains/assess/useAssessWords";

export type AddKind = "trainees" | "staff";

/**
 * The one "Add people" sheet: trainees (one person or a spreadsheet) or staff
 * (an invitation or a spreadsheet). It wraps the two existing panels, so their
 * rules (duplicates reported, never fatal) stay where they were.
 */
export function AddPeopleSheet({
  orgSlug,
  initialKind,
  cohorts,
  canManage,
  onTraineesAdded,
  onStaffAdded,
  onClose,
}: {
  orgSlug: string;
  initialKind: AddKind;
  cohorts: Cohort[];
  canManage: boolean;
  onTraineesAdded: () => void;
  onStaffAdded: () => void;
  onClose: () => void;
}) {
  const w = useAssessWords();
  const [kind, setKind] = useState<AddKind>(initialKind);
  return (
    <Modal onClose={onClose} title={w.addPeople} width="48rem">
      <ModalContent>
        <ModalTitle>{w.addPeople}</ModalTitle>
        <p className="mt-1 text-osce-body text-b2b-mid">
          Add the {w.trainees} who will sit your exams or training sessions, or invite staff to run
          and mark them.
        </p>
        <div className="mt-4 flex flex-col gap-4">
          <TabStrip
            tabs={[
              { key: "trainees" as const, label: w.Trainees },
              { key: "staff" as const, label: "Staff" },
            ]}
            active={kind}
            onSelect={setKind}
            label="Who to add"
          />
          {kind === "trainees" ? (
            <AddTraineePanel
              orgSlug={orgSlug}
              cohorts={cohorts}
              canManage={canManage}
              onAdded={onTraineesAdded}
            />
          ) : (
            <InvitePanel orgSlug={orgSlug} canManage={canManage} onInvited={onStaffAdded} />
          )}
        </div>
        <ModalFooterActions className="mt-6">
          <ModalSecondaryButton onClick={onClose}>Done</ModalSecondaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}
