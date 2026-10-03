"use client";

import { useState } from "react";
import { HiOutlineUsers } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { LivePracticeModal } from "@/capabilities/peer-practice/queue/modals";
import type { Queue } from "@/capabilities/peer-practice/support/useQueue";

/**
 * "Live practice": a secondary button and the prompt behind it.
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
      <Button type="button" variant="secondary" onClick={() => setShowModal(true)} className="gap-1.5">
        <HiOutlineUsers className="h-4 w-4 shrink-0" aria-hidden />
        <span>Live practice</span>
      </Button>

      <LivePracticeModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onStartNow={() => void handleJoinQueue()}
        isJoiningQueue={isJoiningQueue}
      />
    </>
  );
}
