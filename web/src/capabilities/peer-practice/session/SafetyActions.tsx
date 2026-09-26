"use client";

import { useState, type ReactNode } from "react";
import { HiOutlineExclamationTriangle, HiOutlineInformationCircle } from "react-icons/hi2";
import Alert from "@/foundation/forms/Alert";
import {
  Button,
  ConfirmModal,
  Modal,
  ModalContent,
  ModalFooterActions,
  ModalHeader,
  ModalPrimaryButton,
  ModalSecondaryButton,
} from "@/foundation/ui";
import { b2cCard, b2cInputBase } from "@/foundation/ui/productTokens";
import { reportPracticeAbuse, reportPracticeNoShow } from "../api";
import { failureText } from "../support/failure";

const REPORT_FAILED = "Failed to submit report. Please try again.";

/**
 * "Report abuse" in the session header during the consultation and debrief,
 * and the modal it opens. The report goes to the team with both people's
 * details; it blocks nobody, as it never did.
 */
export function ReportAbuseButton({ sessionId, className = "" }: { sessionId: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const submit = async () => {
    if (loading) return;
    const trimmed = note.trim();
    if (!trimmed) {
      setError("Please provide details about what happened.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await reportPracticeAbuse(sessionId, trimmed);
      setNote("");
      setSuccess("Report sent. Our team has been notified and will respond.");
    } catch (cause) {
      setError(failureText(cause, REPORT_FAILED));
    } finally {
      setLoading(false);
    }
  };

  const close = () => {
    setOpen(false);
    setError(null);
    setNote("");
    setSuccess(null);
  };

  return (
    <div className={className}>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="gap-2"
        title="Report abuse or harassment"
      >
        <HiOutlineExclamationTriangle className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
        <span>Report abuse</span>
      </Button>
      {open && (
        <Modal width="500px" height="fit-content" onClose={close}>
          <ModalContent>
            <ModalHeader
              title="Report abuse or harassment"
              description="We'll send your and your partner's details to our team. We take these reports seriously and will respond. Please describe what happened below."
            />
            <label htmlFor="report-abuse-note" className="mb-1 mt-3 block text-osce-meta font-medium text-osce-ink-500">
              Details <span className="text-osce-danger">*</span>
            </label>
            <textarea
              id="report-abuse-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Describe what happened..."
              rows={4}
              maxLength={2000}
              className={b2cInputBase}
            />
            <p className="mb-1 mt-1 text-osce-meta text-osce-ink-500">{note.length}/2000 characters</p>
            <ModalFooterActions className="flex-col-reverse sm:flex-row">
              <ModalSecondaryButton onClick={close} disabled={loading}>
                Cancel
              </ModalSecondaryButton>
              <ModalPrimaryButton onClick={() => void submit()} disabled={loading}>
                {loading ? "Submitting..." : "Submit report"}
              </ModalPrimaryButton>
            </ModalFooterActions>
            {success && <Alert message={success} type="success" className="mt-3" />}
            {error && <Alert message={error} type="error" className="mt-3" />}
          </ModalContent>
        </Modal>
      )}
    </div>
  );
}

/**
 * The guidelines card on the waiting screen, with the no-show report under it.
 * Once the report is sent the card gives way to `afterReport`, which offers a
 * new partner.
 */
export function NoShowGuidelines({ sessionId, afterReport }: { sessionId: string; afterReport: ReactNode }) {
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const report = async () => {
    if (loading) return;
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await reportPracticeNoShow(sessionId);
      setConfirming(false);
      setSuccess("Report sent successfully. Our team has been notified and we'll follow up with your partner.");
    } catch (cause) {
      setError(failureText(cause, REPORT_FAILED));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {success && (
        <div className="mb-4 w-full max-w-md space-y-4">
          <Alert message={success} type="success" className="mb-0" />
          <p className="text-osce-body text-b2c-text-secondary">Find a new practice partner now:</p>
          <div className="flex justify-center">{afterReport}</div>
        </div>
      )}
      {error && !confirming && (
        <div className="mb-4 w-full max-w-md">
          <Alert message={error} type="error" className="mb-0" />
        </div>
      )}
      {!success && (
        <div className={`w-full max-w-md overflow-hidden text-left ${b2cCard}`}>
          <div className="flex items-center gap-2 border-b border-b2c-border bg-b2c-surface-muted px-4 py-3">
            <HiOutlineInformationCircle className="h-4 w-4 flex-shrink-0 text-b2c-text-muted" />
            <span className="text-osce-body font-medium text-b2c-text-secondary">Guidelines</span>
          </div>
          <div className="space-y-4 p-4 sm:p-5">
            <ul className="list-inside list-disc space-y-2 text-osce-body text-b2c-text-secondary">
              <li>
                Please wait up to <strong className="text-osce-ink-900">10 minutes</strong> for your partner to join.
              </li>
              <li>
                If your partner doesn&apos;t show{" "}
                <strong className="text-osce-ink-900"> 10 minutes beyond the scheduled time </strong>, please report a
                no-show so we can follow up.
              </li>
            </ul>
            <Button type="button" variant="primary" size="md" className="w-full" onClick={() => setConfirming(true)}>
              Partner didn&apos;t show? Report no-show
            </Button>
          </div>
        </div>
      )}
      <ConfirmModal
        isOpen={confirming}
        onCancel={() => {
          setConfirming(false);
          setError(null);
        }}
        onConfirm={() => void report()}
        title="Report no-show?"
        message={
          <>
            <p>
              We&apos;ll send your partner&apos;s details to our team to follow up. We can try and find you a new
              practise partner if you would like.
            </p>
            {error && (
              <div className="mt-3">
                <Alert message={error} type="error" className="mb-0" />
              </div>
            )}
          </>
        }
        confirmText={loading ? "Submitting..." : "Yes, report no-show"}
        cancelText="Cancel"
      />
    </>
  );
}
