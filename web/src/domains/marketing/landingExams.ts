"use client";

import { useCallback } from "react";

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

export function buildExamUrl(
  exam: ExamKey,
  hostname: string,
  port?: string,
  protocol?: string,
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
    : "osceguide.com";

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
