"use client";

import { useState } from "react";
import { HiOutlineStar } from "react-icons/hi2";
import { Alert, Button, Modal, ModalContent, ModalLead, ModalFooterActions, ModalPrimaryButton, ModalSecondaryButton } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { SafetyActions } from "./SafetyActions";

export function SessionFeedback({ sessionId, busy, error, onSubmit, onLeave, onRequeue, partnerEnded }: {
  sessionId: string; busy: boolean; error: Error | null; onSubmit: (rating: number, comment: string | null, wouldPracticeAgain: boolean | null) => Promise<boolean>;
  onLeave: () => void; onRequeue?: () => void; partnerEnded: boolean;
}) {
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [again, setAgain] = useState(false);
  const [noticeOpen, setNoticeOpen] = useState(partnerEnded);
  const [sent, setSent] = useState(false);
  return <div className="mx-auto max-w-2xl space-y-5 p-6">
    {noticeOpen && <Modal onClose={() => setNoticeOpen(false)} title="Session ended" width="min(95vw, 480px)" height="fit-content">
      <ModalContent>
        <ModalLead title="Session ended" description="Your partner ended the session, or the session is no longer active. Would you like to find a new practice partner?" />
        <ModalFooterActions>
          <ModalSecondaryButton onClick={() => setNoticeOpen(false)}>Leave feedback</ModalSecondaryButton>
          {onRequeue && <ModalPrimaryButton onClick={onRequeue}>Join queue again</ModalPrimaryButton>}
        </ModalFooterActions>
      </ModalContent>
    </Modal>}
    <h1 className="text-xl font-semibold">{partnerEnded ? "Session ended" : "Session completed"}</h1>
    {partnerEnded && <Alert tone="info">Your partner ended the session, or the session is no longer active.</Alert>}
    <p>Thank you for practising together.</p>
    {sent ? <Alert tone="success">Thank you! Your feedback has been submitted.</Alert> :
      <form className="space-y-4" onSubmit={async (event) => {
        event.preventDefault();
        if (rating !== null && await onSubmit(rating, comment.trim() || null, again)) setSent(true);
      }}>
        <h2 className="font-semibold">Colleague Practice Session Feedback</h2>
        <p>Help us improve! Share your experience of practising with your colleague.</p>
        <fieldset><legend>How would you rate your overall experience?</legend>
          <div className="flex gap-2">{[1, 2, 3, 4, 5].map((value) => <button key={value} type="button" aria-label={`${value} star${value === 1 ? "" : "s"}`} aria-pressed={rating === value}
            onClick={() => setRating(value)} className={`p-3 ${rating !== null && value <= rating ? "text-accent" : "text-ink-muted"}`}><HiOutlineStar className="h-6 w-6" /></button>)}</div>
        </fieldset>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={again} onChange={(event) => setAgain(event.target.checked)} className="h-4 w-4" />
          I would practise with a partner again
        </label>
        <label className="block" htmlFor="peer-feedback-comment">Additional feedback (optional)</label>
        <textarea id="peer-feedback-comment" value={comment} onChange={(event) => setComment(event.target.value)} maxLength={500} rows={3} className="w-full rounded border border-border bg-surface p-3" />
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        <Button type="submit" disabled={busy || rating === null} isLoading={busy}>Submit feedback</Button>
      </form>}
    <SafetyActions sessionId={sessionId} />
    <div className="flex flex-wrap gap-3">
      {onRequeue && <Button variant="primary" onClick={onRequeue}>Join queue again</Button>}
      <Button variant="secondary" onClick={onLeave}>Back to practice</Button>
    </div>
  </div>;
}
