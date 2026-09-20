"use client";

import { useState } from "react";
import { Alert, Button } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import type { Queue } from "../support/useQueue";
import { QueueExpiredModal, QueueIndicator, QueueWaitingModal } from "./modals";

export function QueueOverlay({ queue }: { queue: Queue }) {
  const [minimised, setMinimised] = useState(false);
  return <>
    {queue.error && <Alert tone="danger">
      {errorMessage(queue.error)} <Button size="sm" onClick={queue.retry}>Retry</Button>
    </Alert>}
    {queue.phase === "waiting" && (minimised ?
      <QueueIndicator waitingCount={queue.status?.waiting_count ?? 0}
        onCancel={() => void queue.leave()} onDismiss={() => setMinimised(false)} /> :
      <QueueWaitingModal status={queue.status} live={queue.live}
        onCancel={() => void queue.leave()} onKeepWaiting={() => setMinimised(true)} />)}
    {queue.expired && <QueueExpiredModal onClose={queue.reset} />}
  </>;
}
