"use client";

import type { Dispatch, SetStateAction } from "react";
import { Input, Panel, cn } from "@/foundation/ui";
import { toggleInSet } from "@/domains/assess/support";
import {
  BREAK_MINUTES_BOUNDS,
  READING_MINUTES_BOUNDS,
  breakPositions,
} from "@/domains/assess/timing";

/** Reading and consultation length, side by side. */
export function DurationFields({
  reading,
  setReading,
  simulation,
  setSimulation,
}: {
  reading: number;
  setReading: (minutes: number) => void;
  simulation: number;
  setSimulation: (minutes: number) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <Input
        label="Reading (minutes)"
        type="number"
        min={READING_MINUTES_BOUNDS.min}
        max={READING_MINUTES_BOUNDS.max}
        value={reading}
        onChange={(event) => setReading(Number(event.target.value))}
      />
      <Input
        label="Consultation (minutes)"
        type="number"
        min={1}
        value={simulation}
        onChange={(event) => setSimulation(Number(event.target.value))}
      />
    </div>
  );
}

/** An exam's breaks: one length for the circuit, and which gaps between stations take one. */
export function BreaksPanel({
  stationCount,
  breakMinutes,
  setBreakMinutes,
  breaks,
  setBreaks,
}: {
  stationCount: number;
  breakMinutes: number;
  setBreakMinutes: (minutes: number) => void;
  breaks: Set<number>;
  setBreaks: Dispatch<SetStateAction<Set<number>>>;
}) {
  const gaps = breakPositions(stationCount);
  return (
    <Panel
      title="Breaks"
      description="A break goes between two stations, never after the last one. Everyone on the circuit pauses during it."
    >
      <div className="flex flex-col gap-4">
        <div className="max-w-[13rem]">
          <Input
            label="Break length (minutes)"
            type="number"
            min={BREAK_MINUTES_BOUNDS.min}
            max={BREAK_MINUTES_BOUNDS.max}
            value={breakMinutes}
            onChange={(event) => setBreakMinutes(Number(event.target.value))}
          />
        </div>
        {gaps.length === 0 ? (
          <p className="text-sm text-ink-muted">Add a second station before adding a break.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {gaps.map((position) => {
              const on = breaks.has(position);
              return (
                <li key={position}>
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => setBreaks((current) => toggleInSet(current, position))}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm",
                      on
                        ? "border-b2b-headline bg-b2b-headline text-ink-inverse"
                        : "border-b2b-border bg-b2b-surface text-b2b-mid hover:text-b2b-headline",
                    )}
                  >
                    After station {position}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Panel>
  );
}
