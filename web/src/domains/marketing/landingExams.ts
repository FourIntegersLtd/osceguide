"use client";

import { useCallback } from "react";
import { SITE_HOSTNAME } from "@/foundation/config/siteUrl";

export type ExamKey = "sca" | "plab" | "ortho";

export type LandingExam = {
  key: ExamKey;
  title: string;
  description: string;
};

export const LANDING_EXAMS: LandingExam[] = [
  {
    key: "sca",
    title: "SCA Exam",
    description:
      "Specialized training for the RCGP SCA exam with AI-powered feedback.",
  },
  {
    key: "plab",
    title: "PLAB 2",
    description:
      "Comprehensive preparation with realistic patient scenarios and structured feedback.",
  },
  {
    key: "ortho",
    title: "Orthopaedic ST3",
    description: "Voice-first prep for the orthopaedic ST3 Interviews.",
  },
];

/**
 * Build the URL an exam's landing card should navigate to.
 *
 * `siteHostnameOverride` defaults to `SITE_HOSTNAME` (this deployment's own
 * host — production's `osceguide.com`, or staging's `staging.osceguide.com`)
 * rather than a literal "osceguide.com": a click on staging must land on
 * `{exam}.staging.osceguide.com`, not send the visitor to production. The
 * parameter exists only so a test can assert every deployment shape with a
 * literal value, without mutating `process.env`; real callers never pass it.
 */
export function buildExamUrl(
  exam: ExamKey,
  hostname: string,
  port?: string,
  protocol?: string,
  siteHostnameOverride: string = SITE_HOSTNAME,
): string {
  const normalizedHost = hostname.toLowerCase();
  const isLocal =
    normalizedHost.endsWith("lvh.me") ||
    normalizedHost === "localhost" ||
    normalizedHost === "127.0.0.1" ||
    normalizedHost === "::1";

  const baseDomain = isLocal
    ? port
      ? `lvh.me:${port}`
      : "lvh.me:3000"
    : siteHostnameOverride;

  const scheme = protocol
    ? protocol.replace(":", "")
    : isLocal
      ? "http"
      : "https";

  return `${scheme}://${exam}.${baseDomain}`;
}

export function useExamNavigation() {
  const handleExamClick = useCallback((exam: ExamKey) => {
    if (typeof window === "undefined") {
      return;
    }
    const destination = buildExamUrl(
      exam,
      window.location.hostname,
      window.location.port,
      window.location.protocol,
    );
    window.location.href = destination;
  }, []);

  return { handleExamClick };
}
