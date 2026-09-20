"use client";

import { useState } from "react";
import { Button, ButtonLink, Modal, ModalContent, ModalLead } from "@/foundation/ui";
import { useCurrentExam } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { usePeerPractice } from "./PeerPracticeProvider";
import { LivePracticeButton } from "./queue/LivePracticeButton";

export function PracticeOptions() {
  const shared = usePeerPractice();
  const { code } = useCurrentExam();
  const { hrefFor } = useSurface();
  const [open, setOpen] = useState(false);
  if (!shared) return null;
  return <>
    <Button variant="secondary" onClick={() => setOpen(true)}>Practice with colleague</Button>
    {open && <Modal onClose={() => setOpen(false)} width="min(95vw, 480px)" height="fit-content">
      <ModalContent>
        <ModalLead title="Practise with colleagues" description="Find a colleague now, or schedule a practice session for later." />
        <div className="flex flex-col gap-3">
          <LivePracticeButton queue={shared.queue} examCode={code || null} onStarted={() => setOpen(false)} />
          <ButtonLink href={hrefFor("/peers")} onClick={() => setOpen(false)}>Schedule practice</ButtonLink>
        </div>
      </ModalContent>
    </Modal>}
  </>;
}
