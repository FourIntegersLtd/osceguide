"use client";

import { useId, useState } from "react";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { b2bTokens, cn, Modal } from "@/foundation/ui";
import { acts } from "@/domains/assess/ui";
import { boardBtn } from "@/foundation/ui/boardKit";
import { cardTitle } from "@/domains/assess/chrome";

const COPY = {
  training: {
    title: "Running a practice circuit",
    intro:
      "The circuit runs itself on the clock you set. You watch it, and step in when something needs a human.",
    points: [
      "Start the circuit to open the room; everybody joins from their own screen.",
      "Reading time and the patient follow the server's clock, not this browser.",
      "Pause, extend, resend or jump when you need to. Each one asks why, and your answer is saved.",
    ],
  },
  exam: {
    title: "Observing an examination",
    intro:
      "One candidate, every station, on the examination's own clock. You are here to watch it and to mark it.",
    points: [
      "Station progress updates as the candidate finishes each one.",
      "Listening in is subscribe-only.",
      "Mark a station from its row as soon as it has been sat.",
    ],
  },
} as const;

/**
 * What this screen is for, on the screen itself.
 *
 * Kept from the retiring runner, which learnt the hard way that a supervisor
 * meeting an examination hall for the first time will not have read anything
 * beforehand.
 */
export function RunnerHelpPanel({ kind }: { kind: "training" | "exam" }) {
  const [open, setOpen] = useState(false);
  const titleId = useId();
  const copy = COPY[kind];

  return (
    <div className="shrink-0">
      <button
        type="button"
        aria-haspopup="dialog"
        aria-label={copy.title}
        onClick={() => setOpen(true)}
        className={b2bTokens.b2bIconButtonSm}
      >
        <HiOutlineInformationCircle className="h-5 w-5" aria-hidden />
      </button>

      {open ? (
        <Modal onClose={() => setOpen(false)} labelledBy={titleId} hideCloseButton width="35.5rem" panelClassName="max-w-[35.5rem]" bodyClassName="p-6">
          <div className="flex flex-col gap-3.5">
            <h2 id={titleId} className={`${cardTitle} !leading-tight`}>{copy.title}</h2>
            <p className="m-0 text-assess-label leading-normal text-osce-ink-500">{copy.intro}</p>
            <ul className="m-0 list-disc pl-[18px] text-assess-label leading-normal text-osce-ink-500">
              {copy.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
            <div className={cn(acts, "justify-end")}>
              <button type="button" className={boardBtn()} onClick={() => setOpen(false)}>
                Dismiss help
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
