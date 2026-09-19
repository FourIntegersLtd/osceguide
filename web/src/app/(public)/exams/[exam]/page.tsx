import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { ReactElement } from "react";
import {
  BaseLandingPage,
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
  classic: () => <LandingPage />,
  ortho: () => <OrthoLandingPage />,
  plab: () => <PlabLandingPage />,
  sca: () => <ScaLandingPage />,
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ exam: string }>;
}): Promise<Metadata> {
  const { exam } = await params;
  if (exam === "avodeck") {
    return {
      title: "AvoDeck. Find RCGP CSA Practice Partners | OSCE Guide",
      description:
        "Match with GP trainees for structured CSA practice sessions. Session transcripts, AI cases, NHS-verified users.",
    };
  }
  const name = exam.charAt(0).toUpperCase() + exam.slice(1).toUpperCase();
  return { title: `${name} ${exam === "ortho" ? "Interviews" : "Exam"} | OSCE Guide` };
}

export default async function Page({ params }: { params: Promise<{ exam: string }> }) {
  const { exam } = await params;
  const render = EXAM_PAGES[exam];
  if (!render) notFound();
  return render();
}
