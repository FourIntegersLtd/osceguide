import { PILOT_EXAMS } from "@/domains/marketing/support/partnerConstants";
import type { PilotExam } from "@/domains/marketing/support/partnerTypes";
import { getExamFromHost } from "@/foundation/routing/examFromHost";

export { getExamFromHost };

const PILOT_EXAM_SET = new Set<string>(PILOT_EXAMS);

/** Resolve a pilot exam slug from the request host, or null if not a pilot subdomain. */
export function resolvePilotExamFromHost(
  host: string | null | undefined,
): PilotExam | null {
  const exam = getExamFromHost(host);
  if (exam && PILOT_EXAM_SET.has(exam)) {
    return exam as PilotExam;
  }
  return null;
}
