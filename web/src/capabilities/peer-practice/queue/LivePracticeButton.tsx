"use client";

import { useCallback, useState } from "react";
import { HiOutlineInformationCircle, HiOutlineUsers } from "react-icons/hi2";
import { Alert } from "@/foundation/ui";
import { b2cGhostButton } from "@/foundation/ui/productTokens";
import { errorMessage } from "@/foundation/hooks";
import {
  LivePracticeModal,
  PeerPracticeInfoModal,
} from "@/capabilities/peer-practice/queue/modals";
import { LivePracticeExamPicker } from "./LivePracticeExamPicker";
import type { Queue } from "@/capabilities/peer-practice/support/useQueue";

/**
 * Being paired now, from wherever somebody is standing.
 *
 * Every screen that offered this in the retiring client owned its own copy of
 * the join, the modal and the floating indicator, and they had drifted: two of
 * them could not leave the queue they had put you in. There is one control
 * here, and the queue it drives belongs to the screen that mounts it.
 */
export function LivePracticeButton({
  queue,
  examCode,
  label = "Live Practice",
  onStarted,
}: {
  queue: Queue;
  examCode: string | null;
  label?: string;
  onStarted?: () => void;
}) {
  const [selectedExam, setSelectedExam] = useState("");
  const chosenExam = examCode || selectedExam;
  const [prompting, setPrompting] = useState(false);
  const [explaining, setExplaining] = useState(false);

  const joining = queue.phase === "joining";
  const waiting = queue.phase === "waiting";
  const start = useCallback(async () => {
    if (!chosenExam) { setExplaining(false); setPrompting(true); return; }
    if ("Notification" in window && Notification.permission === "default") {
      void Notification.requestPermission().catch(() => {});
    }
    await queue.join(chosenExam);
    onStarted?.();
    setPrompting(false);
    setExplaining(false);
  }, [chosenExam, queue, onStarted]);

  return (
    <>
      <div className="flex w-full items-center gap-3 sm:w-auto">
        <button
          type="button"
          disabled={joining || waiting || queue.restoring || queue.phase === "matched"}
          onClick={() => setPrompting(true)}
          className={`flex w-full items-center justify-center gap-2 px-4 py-3 text-center text-osce-body sm:w-auto ${b2cGhostButton}`}
        >
          <HiOutlineUsers className="h-5 w-5 shrink-0 sm:h-6 sm:w-6" />
          <span>{waiting ? "In the queue" : label}</span>
        </button>
        <button
          type="button"
          onClick={() => setExplaining(true)}
          className="p-2 text-b2c-text-muted transition-colors hover:text-osce-accent-hover"
          title="Learn more about practising with a colleague"
          aria-label="Learn more about practising with a colleague"
        >
          <HiOutlineInformationCircle className="h-5 w-5" />
        </button>
      </div>

      {queue.error && !waiting ? (
        <Alert tone="danger" className="mt-2">
          {errorMessage(queue.error)}
        </Alert>
      ) : null}

      <LivePracticeModal
        isOpen={prompting}
        onClose={() => setPrompting(false)}
        onStartNow={start}
        isJoiningQueue={joining}
        canStart={Boolean(chosenExam)}
      >
        {!examCode && <LivePracticeExamPicker value={selectedExam} onChange={setSelectedExam} />}
      </LivePracticeModal>

      {explaining && (
        <PeerPracticeInfoModal
          isLoading={joining}
          canStart
          onClose={() => setExplaining(false)}
          onStartPractice={start}
        />
      )}

    </>
  );
}
