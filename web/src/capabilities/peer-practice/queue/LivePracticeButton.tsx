"use client";

import { useCallback, useState } from "react";
import { HiOutlineInformationCircle, HiOutlineUsers } from "react-icons/hi2";
import { Alert } from "@/foundation/ui";
import { b2cGhostButton } from "@/foundation/ui/productTokens";
import { errorMessage } from "@/foundation/hooks";
import {
  LivePracticeModal,
  PeerPracticeInfoModal,
  QueueIndicator,
  QueueWaitingModal,
} from "@/capabilities/peer-practice/queue/modals";
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
}: {
  queue: Queue;
  examCode: string | null;
  label?: string;
}) {
  const [prompting, setPrompting] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [minimised, setMinimised] = useState(false);

  const joining = queue.phase === "joining";
  const waiting = queue.phase === "waiting";

  const start = useCallback(async () => {
    if (!examCode) return;
    await queue.join(examCode);
    setPrompting(false);
    setExplaining(false);
    setMinimised(false);
  }, [examCode, queue]);

  return (
    <>
      <div className="flex w-full items-center gap-3 sm:w-auto">
        <button
          type="button"
          disabled={!examCode || joining || waiting}
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
      />

      {explaining && (
        <PeerPracticeInfoModal
          isLoading={joining}
          onClose={() => setExplaining(false)}
          onStartPractice={start}
        />
      )}

      {waiting && !minimised && (
        <QueueWaitingModal
          status={queue.status}
          live={queue.live}
          onCancel={() => void queue.leave()}
          onKeepWaiting={() => setMinimised(true)}
        />
      )}

      {waiting && minimised && (
        <QueueIndicator
          waitingCount={queue.status?.waiting_count ?? 0}
          onCancel={() => void queue.leave()}
          onDismiss={() => setMinimised(false)}
        />
      )}
    </>
  );
}
