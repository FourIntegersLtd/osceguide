import type { Surface } from "@/capabilities";

export type NavBadges = Record<"live" | "results", string | undefined>;

/** Which count chips an organisation's menu may show: only assess and hire, only to people who run circuits. */
export function navBadgeGate(surface: Surface, canRun: boolean, decides: boolean): { live: boolean; results: boolean } {
  const org = (surface === "assess" || surface === "hire") && canRun;
  return { live: org, results: org && decides };
}

/**
 * The chips: "N live" for circuits running, and the number of results needing a decision or release.
 * A zero shows no chip, and a count that was not read (`null`) shows none rather than a wrong one.
 */
export function navBadges(running: number | null, attention: number | null): NavBadges {
  return {
    live: running ? `${running} live` : undefined,
    results: attention ? String(attention) : undefined,
  };
}
