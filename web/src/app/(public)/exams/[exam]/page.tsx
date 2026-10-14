import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { ReactElement } from "react";
import { publicPageMetadata } from "@/app/metadata";
import {
  BaseLandingPage,
  CascLandingPage,
  LandingPage,
  OrthoLandingPage,
  PlabLandingPage,
  ScaLandingPage,
} from "@/domains/marketing";

/**
 * A landing page written for one exam.
 *
 * Each of these sells a different thing to a different doctor — a GP trainee
 * sitting the SCA is not an orthopaedic registrar preparing for interviews —
 * so they are separate pages rather than one page with the nouns swapped.
 * `avodeck` and `classic` are the partner and generic variants.
 */
const EXAM_PAGES: Record<string, () => ReactElement> = {
  avodeck: () => <BaseLandingPage />,
  casc: () => <CascLandingPage />,
  classic: () => <LandingPage />,
  ortho: () => <OrthoLandingPage />,
  plab: () => <PlabLandingPage />,
  sca: () => <ScaLandingPage />,
};

/** Head of each exam page. The root template adds " | OSCE Guide" to every title. */
const EXAM_HEADS: Record<string, { title: string; description: string }> = {
  sca: {
    title: "SCA Exam Practice with AI Patients",
    description:
      "Voice-first AI practice for the RCGP SCA: time management, data gathering and examiner-grade feedback on the SCA grading domains before exam day.",
  },
  plab: {
    title: "PLAB 2 Exam Practice with AI Patients",
    description:
      "Voice-first AI practice for the GMC PLAB 2: data gathering, interpersonal skills and management under timed pressure, with structured feedback.",
  },
  casc: {
    title: "MRCPsych CASC Exam Practice",
    description:
      "Voice-first AI practice for the RCPsych CASC: risk assessment, mental state examination, capacity and communication stations with structured feedback.",
  },
  ortho: {
    title: "Orthopaedic ST3 Interview Practice",
    description:
      "Rehearse orthopaedic ST3 interview stations with AI voice simulations: clinical reasoning, prioritisation, portfolio and communication before interview day.",
  },
  avodeck: {
    title: "AvoDeck. Find RCGP CSA Practice Partners",
    description:
      "Match with GP trainees for structured CSA practice sessions. Session transcripts, AI cases, NHS-verified users.",
  },
  classic: {
    title: "AI patient simulator for OSCE, SCA, PLAB 2 and CASC practice",
    description:
      "OSCE Guide's AI platform simulates real patient interactions, helping doctors sharpen their clinical skills and enhance communication.",
  },
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ exam: string }>;
}): Promise<Metadata> {
  const { exam } = await params;
  const head = EXAM_HEADS[exam];
  if (!head) return {};
  // `/exams/classic` is the homepage's own page, so it points search engines at `/`.
  return publicPageMetadata({ path: exam === "classic" ? "/" : `/exams/${exam}`, ...head });
}

export default async function Page({ params }: { params: Promise<{ exam: string }> }) {
  const { exam } = await params;
  const render = EXAM_PAGES[exam];
  if (!render) notFound();
  return render();
}
