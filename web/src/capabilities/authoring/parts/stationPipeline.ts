"use client";

/**
 * Where a station version stands on its way from a brief to candidates: its
 * steps, the one thing to do next, and the fact-check review behind them.
 */

import { useEffect, useRef, useState } from "react";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import type { RailStep } from "@/foundation/ui";
import {
  checkingLine,
  draftStep,
  factsOf,
  factsStep,
  needsRuling,
  type Facts,
} from "@/capabilities/fact-check";
import { readStationReview, type AuthoringScope } from "@/capabilities/authoring/api";

type Content = Record<string, unknown>;

export type StationStepId = "draft" | "facts" | "publish";

/** Whether the version holds anything written yet. Media keeps its own per-kind test in staff-media/content/steps.ts. */
export function hasDraft(content: Content): boolean {
  return Object.values(content).some((value) =>
    Array.isArray(value)
      ? value.length > 0
      : typeof value === "string"
        ? value.trim() !== ""
        : value !== null && typeof value === "object" && hasDraft(value as Content),
  );
}

/** The steps from a brief to a published version; only the catalogue checks facts. */
export function stationSteps(
  content: Content,
  facts: Facts | null,
  { factCheck, status }: { factCheck: boolean; status: string },
): RailStep<StationStepId>[] {
  const publish: RailStep<"publish"> = {
    id: "publish",
    label: "Publish",
    state: status === "published" ? "done" : "todo",
    note: status === "published" ? "Live" : status === "archived" ? "Archived" : "Not published",
  };
  return factCheck
    ? [draftStep(hasDraft(content)), factsStep(facts), publish]
    : [draftStep(hasDraft(content)), publish];
}

type NextId =
  "wait" | "save" | "fill" | "produce" | "check-facts" | "rule" | "publish" | "new-version";

export type StationNext = {
  id: NextId;
  /** The step this belongs to, which the screen opens on. */
  step: StationStepId;
  /** Where the version stands, in one line. */
  line: string;
};

/** What to do next with a version, from what is stored and whether the screen is ahead of it. */
export function stationNext(
  content: Content,
  facts: Facts | null,
  state: {
    factCheck: boolean;
    status: string;
    producing: boolean;
    checking: boolean;
    unsaved: boolean;
    /** Why the edits cannot be saved yet, if they cannot. */
    saveBlocker: string | null;
  },
): StationNext {
  if (state.producing) {
    return {
      id: "wait",
      step: "draft",
      line: "The agent is working on this version.",
    };
  }
  if (state.checking) return { id: "wait", step: "facts", line: checkingLine(facts) };
  if (state.status === "archived") {
    return {
      id: "new-version",
      step: "publish",
      line: "Archived. Past attempts keep it; start a new draft version to edit.",
    };
  }
  if (state.status === "published") {
    return {
      id: "new-version",
      step: "publish",
      line: "Published and live. Start a new draft version to change it.",
    };
  }
  if (state.unsaved) {
    return {
      id: "save",
      step: "draft",
      line: state.saveBlocker
        ? `Unsaved changes. ${state.saveBlocker}`
        : "You have unsaved changes. Save them before the next step.",
    };
  }
  if (!hasDraft(content)) {
    return state.factCheck
      ? {
          id: "produce",
          step: "draft",
          line: "Say what the station tests below and the agent drafts it.",
        }
      : {
          id: "fill",
          step: "draft",
          line: "Fill in the station below, then save.",
        };
  }
  if (state.factCheck && !facts) {
    return {
      id: "check-facts",
      step: "draft",
      line: "Read the draft, then check its facts against the guidelines.",
    };
  }
  const open = facts?.claims.filter(needsRuling).length ?? 0;
  if (open > 0) {
    return {
      id: "rule",
      step: "facts",
      line: `${open} to resolve: each claim needs your decision, then save.`,
    };
  }
  return {
    id: "publish",
    step: "publish",
    line: "Ready. Publishing makes this version the one candidates are assessed against.",
  };
}

/**
 * A catalogue version's fact-check review, kept current while the agent or a
 * check runs. `onProduced` fires when the agent stops, as its saved content changed.
 */
export function useStationReview(
  scope: AuthoringScope,
  stationId: string,
  version: number,
  enabled: boolean,
  onProduced: () => void,
) {
  const load = useAsync(
    (signal) =>
      enabled ? readStationReview(scope, stationId, version, signal) : Promise.resolve(null),
    [scope, stationId, version, enabled],
  );
  const [facts, setFacts] = useState<Facts | null>(null);
  const [checking, setChecking] = useState(false);
  const [producing, setProducing] = useState(false);
  const wasProducing = useRef(false);

  useEffect(() => {
    if (!load.data) return;
    setFacts(factsOf(load.data.facts));
    setChecking(load.data.checking);
    if (wasProducing.current && !load.data.producing) onProduced();
    wasProducing.current = load.data.producing;
    setProducing(load.data.producing);
  }, [load.data, onProduced]);

  useMeEvents(["station.updated"], (event) => {
    if ((checking || producing) && (event.name === "resync" || event.data.station_id === stationId))
      load.reload();
  });

  return {
    load,
    review: load.data,
    loading: load.loading,
    error: load.error,
    reload: load.reload,
    facts,
    setFacts,
    checking,
    setChecking,
    producing,
    setProducing,
  };
}
