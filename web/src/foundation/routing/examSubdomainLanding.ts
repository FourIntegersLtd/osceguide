import { getExamFromHost } from "@/foundation/routing/examFromHost";

export const SUPPORTED_EXAM_LANDING_SUBDOMAINS = new Set(["sca", "plab", "casc", "ortho"]);

/**
 * When a visitor hits `{exam}.osceguide.com/` (or `{exam}.lvh.me` locally),
 * serve the per-exam landing at `/exams/{exam}` without changing the URL.
 */
export function examLandingRewritePath(
  host: string | null | undefined,
  pathname: string,
): string | null {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  if (normalized !== "/") {
    return null;
  }

  const exam = getExamFromHost(host);
  if (!exam || !SUPPORTED_EXAM_LANDING_SUBDOMAINS.has(exam)) {
    return null;
  }

  return `/exams/${exam}`;
}
