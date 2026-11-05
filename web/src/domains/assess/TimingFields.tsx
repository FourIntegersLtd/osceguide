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

/** An exam's breaks: a default length, which gaps between stations take one, and each break's own length. */
export function BreaksPanel({
  stationCount,
  breakMinutes,
  setBreakMinutes,
  breaks,
  setBreaks,
  breakLengths,
  setBreakLengths,
}: {
  stationCount: number;
  breakMinutes: number;
  setBreakMinutes: (minutes: number) => void;
  breaks: Set<number>;
  setBreaks: Dispatch<SetStateAction<Set<number>>>;
  breakLengths: Record<number, number>;
  setBreakLengths: Dispatch<SetStateAction<Record<number, number>>>;
}) {
  const toggle = (position: number) => {
    // A break turned off forgets its own length, so turning it back on starts at the default.
    if (breaks.has(position)) {
      setBreakLengths(({ [position]: _dropped, ...rest }) => rest);
    }
    setBreaks((current) => toggleInSet(current, position));
  };
  const gaps = breakPositions(stationCount);
  return (
    <Panel
      title="Breaks"
      description="A break goes between two stations, never after the last one. Everyone on the circuit pauses during it."
    >
      <div className="flex flex-col gap-4">
        <div className="max-w-[13rem]">
          <Input
            label="Default break length (minutes)"
            type="number"
            min={BREAK_MINUTES_BOUNDS.min}
            max={BREAK_MINUTES_BOUNDS.max}
            value={breakMinutes}
            onChange={(event) => setBreakMinutes(Number(event.target.value))}
          />
        </div>
        {gaps.length === 0 ? (
          <p className="text-sm text-ink-muted">
            Add a second station before adding a break.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {gaps.map((position) => {
              const on = breaks.has(position);
              return (
                <li
                  key={position}
                  className="flex flex-col items-start gap-1.5"
                >
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => toggle(position)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm",
                      on
                        ? "border-b2b-headline bg-b2b-headline text-ink-inverse"
                        : "border-b2b-border bg-b2b-surface text-b2b-mid hover:text-b2b-headline",
                    )}
                  >
                    After station {position}
                  </button>
                  {on ? (
                    <Input
                      aria-label={`Break length after station ${position} (minutes)`}
                      type="number"
                      inputSize="sm"
                      min={BREAK_MINUTES_BOUNDS.min}
                      max={BREAK_MINUTES_BOUNDS.max}
                      value={breakLengths[position] ?? breakMinutes}
                      onChange={(event) =>
                        setBreakLengths((current) => ({
                          ...current,
                          [position]: Number(event.target.value),
                        }))
                      }
                    />
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Panel>
  );
}
