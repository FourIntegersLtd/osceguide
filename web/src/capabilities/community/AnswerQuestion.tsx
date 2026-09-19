"use client";

import { useCallback, useState, type FormEvent } from "react";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { reply as postReply } from "@/capabilities/community/api";
import { fieldClass, useViewer } from "@/capabilities/community/posts";

/**
 * Answer somebody's question.
 *
 * No audience of its own: a reply inherits the question's, which is what stops
 * a public answer quoting a private thread from publishing it. The backend
 * enforces that; this form simply never offers the choice.
 */
export function AnswerQuestion({
  questionId,
  onAnswerSubmitted,
}: {
  questionId: string;
  onAnswerSubmitted: () => void;
}) {
  const viewer = useViewer();
  const [answerContent, setAnswerContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);

  const submit = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!answerContent.trim() || !viewer.id) {
        setErrorText(
          !viewer.id ? "You must be logged in to post an answer." : "Answer content cannot be empty.",
        );
        return;
      }
      setIsSubmitting(true);
      setErrorText(null);
      setSuccessMessage(null);
      try {
        await postReply(questionId, answerContent);
        setSuccessMessage("Answer submitted successfully!");
        setAnswerContent("");
        onAnswerSubmitted();
      } catch (cause) {
        setErrorText(errorMessage(cause) || "Failed to submit your answer. Please try again.");
      } finally {
        setIsSubmitting(false);
      }
    },
    [answerContent, questionId, viewer.id, onAnswerSubmitted],
  );

  return (
    <form onSubmit={submit}>
      <B2CPanelCard className="mb-24 mt-0">
        <B2CPanelCardHeader>Post your answer</B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-4">
          <div>
            <ModalTitle>Share your thoughts</ModalTitle>
            <ModalHelper>Help a colleague by answering this question.</ModalHelper>
          </div>

          <textarea
            className={`${fieldClass} min-h-[9rem] resize-y`}
            placeholder="Share your knowledge or thoughts..."
            value={answerContent}
            onChange={(event) => setAnswerContent(event.target.value)}
            required
            disabled={!viewer.id || isSubmitting}
            aria-label="Your answer"
          />

          {!viewer.id ? (
            <p className="text-osce-body text-osce-danger">Please log in to post an answer.</p>
          ) : null}

          {successMessage ? <Alert tone="success">{successMessage}</Alert> : null}
          {errorText ? <Alert tone="danger">{errorText}</Alert> : null}
        </B2CPanelCardBody>
        <B2CPanelCardFooter>
          <ModalPrimaryButton type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Submitting..." : "Submit Answer"}
          </ModalPrimaryButton>
        </B2CPanelCardFooter>
      </B2CPanelCard>
    </form>
  );
}
