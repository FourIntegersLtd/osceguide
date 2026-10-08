import { platformRequest, type components } from "@/foundation/platform-client";
import { orgPath } from "@/domains/assess/api";

export type ProgrammeReportRow = components["schemas"]["ProgrammeReportRow"];
export type OrgReporting = components["schemas"]["OrgReporting"];

/** Sittings, candidates and pass rate per programme, across every sitting. */
export function readOrgReporting(slug: string, signal?: AbortSignal): Promise<OrgReporting> {
  return platformRequest<OrgReporting>(`${orgPath(slug)}/reporting`, { signal });
}

/** A pass rate is only honest beside how many decisions it rests on; none released is not zero. */
export function passRateLabel(row: Pick<ProgrammeReportRow, "released" | "passed" | "pass_rate">): string {
  if (row.pass_rate === null || row.released === 0) return "Nothing released yet";
  return `${row.pass_rate}% (${row.passed} of ${row.released} released)`;
}
