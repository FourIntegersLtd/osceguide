"use client";

import { PEER_JOIN_EARLY_MINUTES } from "@/capabilities/peer-practice/limits";
import { HiOutlineArrowPath, HiOutlineCalendarDays, HiOutlineVideoCamera } from "react-icons/hi2";
import {
  Modal,
  ModalBody,
  ModalFooterActions,
  ModalLead,
  ModalList,
  ModalListRow,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalSection,
  ModalSectionBullets,
} from "@/foundation/ui";
import type { Slot } from "@/capabilities/peer-practice/api";
import { longDate, meridiemTime } from "@/capabilities/peer-practice/support/time";

/** Confirming a claim, with what claiming actually does spelled out. */
export function ClaimConfirmationModal({
  slot,
  isClaiming,
  onConfirm,
  onCancel,
}: {
  slot: Slot | null;
  isClaiming: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!slot) return null;

  return (
    <Modal width="500px" height="fit-content" onClose={onCancel}>
      <ModalBody>
        <ModalLead
          title="Confirm claim"
          description="You are about to reserve this practice slot."
          icon={<HiOutlineCalendarDays className="h-5 w-5" />}
        />

        <ModalSection title="Session details" tint="primary">
          <div className="space-y-1.5 text-osce-meta leading-relaxed text-b2c-text-secondary">
            <p>
              <span className="font-medium text-osce-ink-900">Date:</span>{" "}
              {longDate(slot.starts_at)}
            </p>
            <p>
              <span className="font-medium text-osce-ink-900">Time:</span>{" "}
              {meridiemTime(slot.starts_at)}
            </p>
          </div>
        </ModalSection>

        <ModalSection title="What happens when you claim">
          <ModalSectionBullets
            items={[
              <>You&apos;ll be paired with {slot.owner_username || "this user"} for a practice session</>,
              <>Both of you will receive a confirmation</>,
              <>The session will appear in your &quot;Upcoming sessions&quot; tab</>,
              <>You can join the session at the scheduled time</>,
              <>The slot will be reserved for you</>,
            ]}
          />
        </ModalSection>

        <ModalFooterActions>
          <ModalSecondaryButton onClick={onCancel}>Cancel</ModalSecondaryButton>
          <ModalPrimaryButton onClick={onConfirm} disabled={isClaiming} className="gap-2">
            {isClaiming ? (
              <>
                <HiOutlineArrowPath className="h-3.5 w-3.5 animate-spin" /> Claiming...
              </>
            ) : (
              "Claim"
            )}
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalBody>
    </Modal>
  );
}

const STEPS = [
  {
    title: "Post availability",
    text: "Pick a date and time for a video practice. Add an optional note.",
  },
  {
    title: "Someone claims it",
    text: "They claim your slot; you both get confirmed for the video call.",
  },
  {
    title: "Join on the day",
    text: `Join the video call up to ${PEER_JOIN_EARLY_MINUTES} minutes before. Roles (Doctor/Patient) are assigned automatically.`,
  },
  {
    title: "Practice over video",
    text: "Reading time, then simulation. Timers start when both join the call.",
  },
];

export function MarketplaceHowItWorksModal({ onClose }: { onClose: () => void }) {
  return (
    <Modal width="min(95vw, 600px)" height="fit-content" onClose={onClose}>
      <ModalBody>
        <ModalLead
          title="How it works"
          description="Match with colleagues and practice together over video."
          icon={<HiOutlineVideoCamera className="h-5 w-5" />}
        />
        <ModalSection title="Steps">
          <ModalList>
            {STEPS.map((step, index) => (
              <ModalListRow
                key={step.title}
                marker={
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-b2c-surface-muted font-mono text-osce-caption font-semibold text-osce-ink-900">
                    {index + 1}
                  </span>
                }
                title={step.title}
                description={step.text}
              />
            ))}
          </ModalList>
        </ModalSection>
      </ModalBody>
    </Modal>
  );
}
