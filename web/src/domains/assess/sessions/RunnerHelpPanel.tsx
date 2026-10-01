"use client";

import { useState } from "react";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { b2bTokens } from "@/foundation/ui";

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
      "Listening in is subscribe-only: you can hear the consultation and cannot be heard in it.",
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
  const copy = COPY[kind];

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="runner-help"
        aria-label={copy.title}
        onClick={() => setOpen((value) => !value)}
        className={b2bTokens.b2bIconButtonSm}
      >
        <HiOutlineInformationCircle className="h-5 w-5" aria-hidden />
      </button>

      {open ? (
        <>
          <button
            type="button"
            aria-label="Dismiss help"
            className="fixed inset-0 z-10 cursor-default bg-black/10"
            onClick={() => setOpen(false)}
          />
          <div
            id="runner-help"
            role="dialog"
            aria-label={copy.title}
            className="absolute right-0 top-full z-20 mt-2 w-[min(calc(100vw-2rem),24rem)] rounded-lg border border-b2b-border bg-white p-4 text-osce-body leading-relaxed text-b2b-graphite"
          >
            <p className="font-semibold text-b2b-headline">{copy.title}</p>
            <p className="mt-2 text-osce-meta text-b2b-mid">{copy.intro}</p>
            <ul className="mt-3 list-inside list-disc space-y-1.5 text-osce-meta text-b2b-mid">
              {copy.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
        </>
      ) : null}
    </div>
  );
}
