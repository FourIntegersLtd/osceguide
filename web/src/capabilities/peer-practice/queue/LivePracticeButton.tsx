"use client";

import { useState } from "react";
import { HiOutlineUsers } from "react-icons/hi2";
import { b2cGhostButton } from "@/foundation/ui/productTokens";
import { LivePracticeModal } from "@/capabilities/peer-practice/queue/modals";
import type { Queue } from "@/capabilities/peer-practice/support/useQueue";

/**
 * "Live Practice": a ghost button and the prompt behind it.
 *
 * The queue it drives belongs to `PeerPracticeProvider`, which also raises the
 * searching modal and the toasts, so every screen that mounts this button
 * behaves the same way.
 */
export function LivePracticeButton({
  queue,
  examCode,
}: {
  queue: Queue;
  examCode: string | null;
}) {
  const [showModal, setShowModal] = useState(false);
  const [isJoiningQueue, setIsJoiningQueue] = useState(false);

  const handleJoinQueue = async () => {
    if (!examCode) return;
    setIsJoiningQueue(true);
    try {
      await queue.join(examCode);
      setShowModal(false);
    } finally {
      setIsJoiningQueue(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className={`flex w-full items-center justify-center gap-2 px-4 py-3 text-center text-osce-body sm:w-auto ${b2cGhostButton}`}
      >
        <HiOutlineUsers className="h-5 w-5 shrink-0 sm:h-6 sm:w-6" />
        <span>Live Practice</span>
      </button>

      <LivePracticeModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onStartNow={() => void handleJoinQueue()}
        isJoiningQueue={isJoiningQueue}
      />
    </>
  );
}
