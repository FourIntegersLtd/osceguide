"use client";

import { useId, useState } from "react";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { b2bTokens, cn, Modal } from "@/foundation/ui";
import { acts, PEOPLE_DIALOG_SIZE } from "@/domains/assess/ui";
import { boardBtn } from "@/foundation/ui/boardKit";
import { cardTitle } from "@/domains/assess/chrome";
import { useAssessWords } from "@/capabilities/assess-words";

const COPY = {
  training: (circuit: string) => ({
    title: `How this ${circuit} works`,
    intro:
      `The ${circuit} runs itself on the timings you set. You watch it and step in when needed.`,
    points: [
      `Start the ${circuit}. Everyone joins from their own screen.`,
      "One shared timer drives every screen, not this browser.",
      "Pause, add time, resend the patient or move on when needed. Each asks you why.",
    ],
  }),
  exam: () => ({
    title: "Watching an exam",
    intro:
      "One candidate, every station, on the exam's own timer. You watch and mark.",
    points: [
      "The list updates as the candidate finishes each station.",
      "You can listen in. The candidate cannot hear you.",
      "Mark a station from its row once it is done.",
    ],
  }),
};

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
  const w = useAssessWords();
  const copy = COPY[kind](w.circuit);

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
        <Modal onClose={() => setOpen(false)} labelledBy={titleId} hideCloseButton {...PEOPLE_DIALOG_SIZE} bodyClassName="p-6">
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
