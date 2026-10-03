"use client";

import { useCallback, useState, type FormEvent } from "react";
import { Alert, Button, Card, productTokens } from "@/foundation/ui";
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
    <form onSubmit={submit} className="mb-24">
      <Card title="Post your answer" description="Help a colleague by answering this question.">
        <div className="space-y-4">
          <div>
            <label htmlFor="community-answer" className={productTokens.b2cFieldLabel}>Your answer</label>
            <textarea
              id="community-answer"
              className={`${fieldClass} mt-1.5 min-h-[9rem] resize-y`}
              placeholder="Share your knowledge or thoughts..."
              value={answerContent}
              onChange={(event) => setAnswerContent(event.target.value)}
              required
              disabled={!viewer.id || isSubmitting}
            />
          </div>

          {!viewer.id ? (
            <p className="text-osce-meta text-osce-danger-text">Sign in to post an answer.</p>
          ) : null}

          {successMessage ? <Alert tone="success">{successMessage}</Alert> : null}
          {errorText ? <Alert tone="danger">{errorText}</Alert> : null}

          <Button type="submit" isLoading={isSubmitting}>
            Submit answer
          </Button>
        </div>
      </Card>
    </form>
  );
}
