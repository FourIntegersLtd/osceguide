"use client";

import { useMemo } from "react";
import { useAsync, type AsyncState } from "@/foundation/hooks";
import { listExams, type Exam, type LibraryStation } from "@/capabilities/stations";
import {
  listEntitlements,
  listSets,
  loadStationCatalogue,
  type Entitlement,
  type TrialLimits,
  type StationSet,
} from "@/domains/train/api";

export interface MockWorkspace {
  sets: StationSet[];
  exams: Exam[];
  stations: LibraryStation[];
  entitlements: Entitlement[];
  trial: TrialLimits;
  /** Station version id to title. Entries carry a version id and no title. */
  titles: Map<string, string>;
}

/**
 * Everything the practice tabs share, loaded once.
 *
 * The retiring client fetched the station list three times on this screen —
 * once for the setup form's maximum, once for the combine dropdown, once for
 * the progress bar's denominator — because each component asked for itself.
 * One loader above them costs one request and keeps the three tabs telling the
 * same story about how many stations exist.
 */
export function useMockWorkspace(): AsyncState<MockWorkspace> {
  return useAsync(async (signal) => {
    const [sets, exams, library, entitlements] = await Promise.all([
      listSets(signal),
      listExams(signal),
      loadStationCatalogue(null, signal),
      listEntitlements(signal),
    ]);
    return {
      sets: sets.items,
      exams: exams.items,
      stations: library,
      entitlements: entitlements.items,
      trial: entitlements.trial,
      titles: new Map(library.map((station) => [station.version_id, station.title])),
    };
  }, []);
}

/** The station versions of one exam, for a form that may only mix one exam. */
export function useExamStations(
  workspace: MockWorkspace | null,
  examCode: string,
): LibraryStation[] {
  return useMemo(
    () => (workspace?.stations ?? []).filter((station) => station.exam_code === examCode),
    [workspace, examCode],
  );
}

/**
 * Which exam a new session belongs to.
 *
 * The app's exam, not this form's. This used to fall back through the person's
 * first practice set, then the first station in the catalogue, then the first
 * published exam — three guesses, none of which was what the person was
 * sitting, and the form offered the rest of the catalogue beside it.
 *
 * `fallback` is `useCurrentExam().code`. The old fallbacks stay only for the
 * moment before it resolves, so the form is never rendered against nothing.
 */
export function defaultExamCode(workspace: MockWorkspace | null, fallback: string | null): string {
  if (fallback) return fallback;
  if (!workspace) return "";
  const fromSets = workspace.sets[0]?.exam_code;
  if (fromSets) return fromSets;
  return workspace.stations[0]?.exam_code ?? workspace.exams[0]?.code ?? "";
}

export function examByCode(workspace: MockWorkspace | null, code: string): Exam | null {
  return workspace?.exams.find((exam) => exam.code === code) ?? null;
}

/**
 * Whether this person's access is paid-for, and whether it has run out.
 *
 * An entitlement is only a grant: `list_for_user` answers with revoked and
 * expired rows too, so the gate is `live` and the default when nothing is live
 * is "not entitled" rather than "probably fine".
 */
export function accessState(workspace: MockWorkspace | null, examCode: string) {
  if (!workspace) return { hasPaid: undefined, subscriptionExpired: false };
  const forExam = workspace.entitlements.filter((item) => item.exam_code === examCode);
  const live = forExam.some((item) => item.live);
  return { hasPaid: live, subscriptionExpired: !live && forExam.length > 0 };
}
