import { plural } from "@/foundation/format";
import { platformRequest, type components } from "@/foundation/platform-client";
import { orgPath } from "@/domains/assess/api";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

export type ProgrammeReportRow = components["schemas"]["ProgrammeReportRow"];
export type OrgReporting = components["schemas"]["OrgReporting"];
export type StationReportRow = components["schemas"]["StationReportRow"];

/** Sittings, candidates and pass rate per programme, across every sitting. */
export function readOrgReporting(slug: string, signal?: AbortSignal): Promise<OrgReporting> {
  return platformRequest<OrgReporting>(`${orgPath(slug)}/reporting`, { signal });
}

/** A pass rate is only honest beside how many decisions it rests on; none released is not zero. */
function passRateLabel(row: Pick<ProgrammeReportRow, "released" | "passed" | "pass_rate">): string {
  if (row.pass_rate === null || row.released === 0) return "Nothing released yet";
  return `${row.pass_rate}% (${row.passed} of ${row.released} released)`;
}

/** "1 sitting · 1 candidate · Nothing released yet"; an employer reads "1 assessment · 1 candidate". */
export function reportingLine(
  row: Pick<ProgrammeReportRow, "sittings" | "candidates" | "released" | "passed" | "pass_rate">,
  w: AssessWords,
): string {
  return `${plural(row.sittings, w.sitting, w.sittings)} · ${plural(row.candidates, "candidate")} · ${passRateLabel(row)}`;
}

export type ReportTile = { label: string; value: string };

/** The employer's tiles, summed over every exam: candidates assessed, how many passed, assessments held. */
export function reportTiles(rows: readonly ProgrammeReportRow[], w: AssessWords): ReportTile[] {
  const sum = (pick: (row: ProgrammeReportRow) => number) => rows.reduce((total, row) => total + pick(row), 0);
  const released = sum((row) => row.released);
  return [
    { label: `${w.Trainees} assessed`, value: String(sum((row) => row.candidates)) },
    { label: "Passed", value: released === 0 ? "-" : `${Math.round((sum((row) => row.passed) / released) * 100)}%` },
    { label: w.Sittings, value: String(sum((row) => row.sittings)) },
  ];
}

/** The employer's fourth tile: different assessors who have completed a review. */
export const assessorsTile = (count: number): ReportTile => ({ label: "Assessors marking", value: String(count) });

export const STATION_TABLE_HEADS = ["Station", "Pass rate", "Weakest competency"] as const;

/** One station row as the table prints it: a whole-number pass rate, and a dash where nothing is known. */
export function stationCells(row: StationReportRow): [string, string, string] {
  return [row.station_title, row.pass_rate === null ? "-" : `${Math.round(row.pass_rate)}%`, row.weakest_competency ?? "-"];
}

export const HIRE_REPORTING = {
  description: "How candidates did across your released assessments, and where they struggle.",
  note: "Built from results, so Training and Formal exam assessments both count. Hiring decisions are not part of this page.",
  emptyTitle: "Nothing to report yet",
  emptyBody: "Reporting starts once you release the results of an assessment.",
  emptyLink: "Go to results",
} as const;
