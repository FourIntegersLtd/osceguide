"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray, HiOutlineChatBubbleLeftRight } from "react-icons/hi2";
import { Alert, Button, Card, Spinner } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { downloadTranscript } from "@/capabilities/attempt-runner/transcriptDocument";
import { readAttemptTranscript } from "@/domains/assess/api";
import { TranscriptView } from "@/capabilities/feedback";

/**
 * What was actually said, for the person marking it.
 *
 * The reviewer's screen had the machine's marking on it and nothing else: the
 * transcript route was owner-or-platform-admin, so the examiner sitting two
 * metres from the candidate could not read the consultation they were being
 * asked to grade. That is now open to the supervisor named on the attempt's
 * circuit and to nobody broader, which is what makes this panel honest about
 * why it may fail.
 *
 * Loaded on the click rather than with the screen. A transcript is the longest
 * thing an attempt carries and most reviews are settled from the marking
 * beside it, so pulling every consultation into every page load would cost the
 * institution for a document only sometimes wanted.
 */
export function AttemptTranscript({ attemptId }: { attemptId: string | null }) {
  const [wanted, setWanted] = useState(false);
  const state = useAsync(
    (signal) =>
      wanted && attemptId ? readAttemptTranscript(attemptId, signal) : Promise.resolve(null),
    [wanted, attemptId],
  );

  if (!attemptId) return null;

  if (!wanted) {
    return (
      <Card
        title="What was said"
        description="The consultation itself, not the scoring of it."
      >
        <Button variant="secondary" size="sm" onClick={() => setWanted(true)}>
          <HiOutlineChatBubbleLeftRight className="mr-2 h-4 w-4 shrink-0" aria-hidden />
          Load the transcript
        </Button>
      </Card>
    );
  }

  if (state.loading) {
    return (
      <Card title="What was said">
        <Spinner label="Loading the transcript" />
      </Card>
    );
  }

  if (state.error) {
    return (
      <Alert
        tone={hasCode(state.error, "attempt_not_yours", "forbidden") ? "warning" : "danger"}
        title="This transcript is not yours to read"
      >
        {hasCode(state.error, "attempt_not_yours", "forbidden")
          ? "Only the supervisor named on this circuit can read what was said in it."
          : errorMessage(state.error)}
      </Alert>
    );
  }

  const transcript = state.data;
  if (!transcript) return null;

  return (
    <Card
      title="What was said"
      description={
        transcript.complete
          ? "The whole consultation, in order."
          : "Still arriving — this is what has been transcribed so far."
      }
    >
      {/*
        Saving is the same act as the candidate's own download, through the same
        helper, so the two copies of one consultation cannot disagree. The
        attempt is in the filename because an examiner keeps these: a folder of
        `transcript.txt` is a folder nobody can attribute later.
      */}
      <div className="mb-3 flex justify-end">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => downloadTranscript(transcript, `transcript-${attemptId}.txt`)}
          disabled={transcript.messages.length === 0}
        >
          <HiOutlineArrowDownTray className="mr-2 h-4 w-4 shrink-0" aria-hidden />
          Download
        </Button>
      </div>
      <div className="max-h-[32rem] overflow-y-auto">
        <TranscriptView transcript={transcript} />
      </div>
    </Card>
  );
}
