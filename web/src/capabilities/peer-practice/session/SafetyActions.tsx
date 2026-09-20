"use client";

import { useState } from "react";
import { Alert, Button, ConfirmModal, Modal, ModalContent, ModalLead, ModalFooterActions, ModalPrimaryButton, ModalSecondaryButton } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { reportPracticeAbuse, reportPracticeNoShow } from "../api";

export function SafetyActions({ sessionId, noShow = false }: { sessionId: string; noShow?: boolean }) {
  const [open, setOpen] = useState(false);
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const submit = async () => {
    if (busy) return;
    if (!noShow && !details.trim()) { setError("Please provide details about what happened."); return; }
    setBusy(true); setError(null);
    try {
      if (noShow) await reportPracticeNoShow(sessionId);
      else await reportPracticeAbuse(sessionId, details.trim());
      setSent(true); setOpen(false);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  };
  return <div>
    <Button size="sm" variant="secondary" disabled={sent} onClick={() => setOpen(true)}>{sent ? "Report sent" : noShow ? "Report no-show" : "Report abuse"}</Button>
    {noShow ? <ConfirmModal isOpen={open} onCancel={() => !busy && setOpen(false)} onConfirm={() => void submit()}
      title="Report partner no-show?" message="If your partner has not joined, you can report their absence. You can keep waiting or end this session."
      confirmText="Report no-show" cancelText="Keep waiting" isLoading={busy} /> : open &&
      <Modal onClose={() => !busy && setOpen(false)} width="min(95vw, 500px)" height="fit-content">
        <ModalContent>
          <ModalLead title="Report abuse or harassment" description="Please describe what happened. Your report is linked to this session and its participants." />
          <label htmlFor="peer-abuse-details">Details</label>
          <textarea id="peer-abuse-details" value={details} onChange={(event) => setDetails(event.target.value)} maxLength={2000} rows={4}
            className="w-full rounded border border-border bg-surface p-3" />
          {error && <Alert tone="danger">{error}</Alert>}
          <ModalFooterActions>
            <ModalSecondaryButton disabled={busy} onClick={() => setOpen(false)}>Cancel</ModalSecondaryButton>
            <ModalPrimaryButton disabled={busy || !details.trim()} onClick={() => void submit()}>{busy ? "Submitting…" : "Submit report"}</ModalPrimaryButton>
          </ModalFooterActions>
        </ModalContent>
      </Modal>}
    {error && noShow && <Alert tone="danger">{error}</Alert>}
  </div>;
}
