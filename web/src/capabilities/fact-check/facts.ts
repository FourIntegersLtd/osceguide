/**
 * A fact check of clinical teaching material as the server stores it
 * (`media_production/service_facts.py`), and the edits a reader makes in answer
 * to it, and the producing agent's run that drafts, checks and corrects it. The
 * media review and platform stations both use it.
 */

import type { RailStep } from "@/foundation/ui";

type Content = Record<string, unknown>;

/** What one source said about a claim. Checks stored before both sources were always asked lack `verdict`. */
export type Evidence = {
  kind: "guideline" | "web";
  verdict?: "supported" | "contradicted" | "not_found";
  why?: string;
  /** Clinical Buddy's labels: "Reliable", "Standard" or "Low", and the kind of source. */
  reliability?: string;
  source_type?: string;
  source: string;
  section: string;
  page: number | null;
  url: string | null;
  quote: string;
};

export type FactVerdict =
  "supported" | "contradicted" | "not_found" | "conflict" | "not_checked";

export type FactClaim = {
  id: string;
  /** The slide of a deck the claim sits on; null anywhere else. */
  slide: number | null;
  /** A station's field the claim sits in, and its name for the reader. */
  field?: string;
  place?: string;
  claim: string;
  verdict: FactVerdict;
  why: string;
  checked: string[];
  evidence: Evidence[];
  /** `old` is null when the words to replace could not be pinned down. */
  suggestion: { old: string | null; new: string } | null;
  /** Set here, by the reader: what they did with the suggestion. */
  decision?: "accepted" | "dismissed";
  /** Set when the producing agent made the correction rather than a reader. */
  by?: "agent";
  /** What an accepted correction swapped, so reopening it can swap it back. */
  swap?: Swap;
};

/** Words in the material (`from`) and what replaced them (`to`); an empty `to` removes them. */
export type Swap = { from: string; to: string };

/** A swap that takes the words out altogether rather than rewording them. */
export function isRemoval(swap: Swap | undefined): boolean {
  return swap !== undefined && swap.to === "";
}

/** How far a check that is still running has got; absent once it has finished. */
export type FactProgress = { done: number; total: number };

export type Facts = {
  checked_at: string;
  claims: FactClaim[];
  progress?: FactProgress;
  /** Who checked it, when a person checked it themselves rather than the platform. */
  checked_by?: string;
};

export function record(value: unknown): Content | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Content)
    : null;
}

export function records(value: unknown): Content[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry: unknown): Content[] => {
    const fields = record(entry);
    return fields ? [fields] : [];
  });
}

/** A stored check, keeping whatever else the server put beside its claims. */
export function factsOf(value: unknown): Facts | null {
  const facts = record(value);
  if (!facts) return null;
  return {
    ...facts,
    checked_at: typeof facts.checked_at === "string" ? facts.checked_at : "",
    claims: records(facts.claims) as unknown as FactClaim[],
    progress: progressOf(facts.progress),
  };
}

function progressOf(value: unknown): FactProgress | undefined {
  const fields = record(value);
  return fields &&
    typeof fields.done === "number" &&
    typeof fields.total === "number"
    ? { done: fields.done, total: fields.total }
    : undefined;
}

/** Where a claim sits, for the reader: "Slide 3", "Examiner notes", or nothing. */
export function placeOf(claim: FactClaim): string | null {
  if (claim.place) return claim.place;
  return claim.slide !== null ? `Slide ${claim.slide}` : null;
}

/** A claim the reader still has to rule on: the sources say it is wrong, or disagree. */
export function needsRuling(claim: FactClaim): boolean {
  return (
    (claim.verdict === "contradicted" || claim.verdict === "conflict") &&
    !claim.decision
  );
}

/** The draft step every produced item starts with, as the step rail shows it. */
export function draftStep(drafted: boolean): RailStep<"draft"> {
  return {
    id: "draft",
    label: "Draft",
    state: drafted ? "done" : "todo",
    note: drafted ? "Written" : "Nothing written yet",
  };
}

/** The fact-check step as the step rail shows it. `unchecked` is its note before any check is on record. */
export function factsStep(facts: Facts | null, unchecked = "Not checked"): RailStep<"facts"> {
  const open = facts?.claims.filter(needsRuling).length ?? 0;
  return {
    id: "facts",
    label: "Check facts",
    state: !facts ? "todo" : open > 0 ? "attention" : "done",
    note: !facts
      ? unchecked
      : open > 0
        ? `${open} to resolve`
        : `${facts.claims.length} claims checked${facts.checked_by ? " by hand" : ""}`,
  };
}

/** What a running check says it is doing, with how far it has got once the server reports it. */
export function checkingLine(facts: Facts | null): string {
  const progress = facts?.progress;
  return progress
    ? `Checking facts, ${progress.done} of ${progress.total} claims…`
    : "Checking facts against the guidelines…";
}

/** A line left holding nothing but a list marker or a speaker's name once words were removed from it. */
const EMPTIED_LINE = /^\s*(?:[-*•]|\d+[.)]|[A-Z][\w ]{0,30}:)?\s*$/;

/**
 * `text` with `old` swapped for `next`. A removal also drops each line it leaves empty, and only
 * those: blank lines and headings elsewhere stay.
 */
function swappedIn(text: string, old: string, next: string): string {
  if (next || old.includes("\n")) return text.split(old).join(next);
  return text
    .split("\n")
    .flatMap((line) => {
      if (!line.includes(old)) return [line];
      const left = line.split(old).join("");
      return EMPTIED_LINE.test(left) ? [] : [left];
    })
    .join("\n");
}

/** Every string under `value` with `old` swapped for `next`; what is spoken, and the review itself, are left alone. */
function replaced(
  value: unknown,
  old: string,
  next: string,
  key = "",
): unknown {
  if (key === "review" || key === "narration" || key === "presentation")
    return value;
  if (typeof value === "string") return swappedIn(value, old, next);
  if (Array.isArray(value))
    // A list entry a removal empties goes from the list, rather than staying as a blank bullet.
    return value
      .map((entry) => replaced(entry, old, next))
      .filter((entry, at) => next || entry !== "" || value[at] === "");
  const fields = record(value);
  if (!fields) return value;
  return Object.fromEntries(
    Object.entries(fields).map(([name, entry]) => [
      name,
      replaced(entry, old, next, name),
    ]),
  );
}

/** `content` with `swap.from` replaced by `swap.to` where the claim sits. */
export function corrected(
  content: Content,
  claim: FactClaim,
  swap: Swap,
): Content {
  const slides = Array.isArray(content.slides) ? content.slides : null;
  if (claim.slide !== null && slides) {
    return {
      ...content,
      slides: slides.map((slide, index) =>
        index === (claim.slide ?? 0) - 1
          ? replaced(slide, swap.from, swap.to)
          : slide,
      ),
    };
  }
  if (claim.field && claim.field in content) {
    return {
      ...content,
      [claim.field]: replaced(content[claim.field], swap.from, swap.to),
    };
  }
  return replaced(content, swap.from, swap.to) as Content;
}

/**
 * `content` with an accepted correction taken out again: the original words put back. Removed
 * words cannot be: where they stood is gone.
 */
export function uncorrected(content: Content, claim: FactClaim): Content {
  return claim.decision === "accepted" && claim.swap && !isRemoval(claim.swap)
    ? corrected(content, claim, { from: claim.swap.to, to: claim.swap.from })
    : content;
}

/** `facts` with the reader's ruling on one claim recorded. */
export function ruled(
  facts: Facts,
  claimId: string,
  decision: "accepted" | "dismissed",
  swap?: Swap,
): Facts {
  return {
    ...facts,
    claims: facts.claims.map((claim) =>
      claim.id === claimId
        ? { ...claim, decision, ...(swap ? { swap } : {}) }
        : claim,
    ),
  };
}

/** `facts` with the reader's ruling on one claim taken back, so it needs a ruling again. */
export function reopened(facts: Facts, claimId: string): Facts {
  return {
    ...facts,
    claims: facts.claims.map((claim) => {
      if (claim.id !== claimId) return claim;
      const { decision: _decision, swap: _swap, by: _by, ...open } = claim;
      return open;
    }),
  };
}
