"use client";

import { useState } from "react";
import Link from "next/link";
import {
  HiOutlineClock,
  HiOutlineIdentification,
  HiOutlineMicrophone,
} from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  B2CPanelCardHeaderIcon,
  B2CSegmentedTabs,
  Badge,
  ButtonLink,
} from "@/foundation/ui";
import { b2cBodyText, b2cBodyTextMuted, b2cPageTitle } from "@/foundation/ui/productTokens";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listExams, readLibraryStation } from "@/capabilities/stations/api";
// The thread lives in `community`: it is the same post model as every other
// discussion, with the same likes, the same deletion rule and the same
// audience scoping. Two jobs built this at once and this is the faithful one.
import { StationComments } from "@/capabilities/community";
import { StationNotFound } from "@/capabilities/stations/StationNotFound";
import { libraryHref, practiseHref } from "@/capabilities/stations/routes";
import { useRecordView } from "@/capabilities/account/useRecordView";

type DetailTab = "brief" | "discussion";

/**
 * One station, before it is sat.
 *
 * What the backend will tell a candidate about a station it has not yet
 * started is deliberately thin: the title, the exam and the version. The
 * scenario itself — the brief, the patient's script, the marking guidance — is
 * frozen server-side when an attempt is created and read by the worker, and
 * never travels through the browser, so a tampered payload cannot change what
 * is assessed. That is why the reading period lives inside the consultation
 * rather than on this page.
 */
export function StationDetail({ stationId }: { stationId: string }) {
  const { hrefFor } = useSurface();
  const [tab, setTab] = useState<DetailTab>("brief");

  const station = useAsync((signal) => readLibraryStation(stationId, signal), [stationId]);
  const exams = useAsync(async (signal) => (await listExams(signal)).items, []);
  const exam = exams.data?.find((item) => item.code === station.data?.exam_code) ?? null;
  // By version, the id the tutor's notes and its suggestions use for a station.
  useRecordView(
    station.data
      ? {
          kind: "viewed",
          ref_kind: "station",
          ref_id: station.data.version_id,
          title: station.data.title,
          exam_code: station.data.exam_code,
        }
      : null,
  );

  return (
    <div className="w-full">
      <Link
        href={libraryHref(hrefFor)}
        className="group mb-8 inline-flex items-center text-b2c-text-secondary hover:text-osce-ink-900"
      >
        <span className="mr-2 transition-transform group-hover:-translate-x-1" aria-hidden>
          &larr;
        </span>
        <span>Back to the library</span>
      </Link>

      {/*
       * A link to a station that is gone, or was never this person's, settles on
       * `null` rather than failing — and `AsyncBoundary` renders nothing at all
       * for a null result, which is how a dead link came to look like a blank
       * page. So the sentence is drawn here, above the boundary that has no
       * error to report.
       */}
      {station.data === null && !station.loading && !station.error ? <StationNotFound /> : null}

      <AsyncBoundary state={station}>
        {(found) => (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <h1 className={b2cPageTitle}>{found.title}</h1>
                <p className={`mt-1 ${b2cBodyTextMuted}`}>
                  Version {found.version}
                  {found.published_at
                    ? ` · published ${new Date(found.published_at).toLocaleDateString()}`
                    : ""}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <Badge tone="accent">{(exam?.name ?? found.exam_code).toUpperCase()}</Badge>
                <ButtonLink href={practiseHref(hrefFor, found.id)} className="gap-2">
                  <HiOutlineMicrophone className="h-4 w-4" aria-hidden />
                  <span>Practise this station</span>
                </ButtonLink>
              </div>
            </div>

            <B2CSegmentedTabs<DetailTab>
              aria-label="Station"
              value={tab}
              onChange={setTab}
              items={[
                { id: "brief", label: "Overview" },
                { id: "discussion", label: "Discussion" },
              ]}
            />

            {tab === "brief" ? (
              <Overview
                readingSeconds={exam?.default_reading_seconds ?? null}
                simulationSeconds={exam?.default_simulation_seconds ?? null}
              />
            ) : null}
            {tab === "discussion" ? <StationComments stationId={found.id} /> : null}
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

function Overview({
  readingSeconds,
  simulationSeconds,
}: {
  readingSeconds: number | null;
  simulationSeconds: number | null;
}) {
  return (
    <B2CPanelCard>
      <B2CPanelCardHeader>
        <B2CPanelCardHeaderIcon icon={HiOutlineIdentification} tone="primary" />
        How this station runs
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        <p className={b2cBodyText}>
          You will read the candidate brief, then speak to a simulated patient. The brief opens
          when the station starts — it is part of the exam, not something to read beforehand.
        </p>
        <ul className="space-y-2">
          <Timing
            label="Reading time"
            seconds={readingSeconds}
            fallback="Set by the exam."
          />
          <Timing
            label="Consultation"
            seconds={simulationSeconds}
            fallback="Set by the exam."
          />
        </ul>
        <p className={b2cBodyTextMuted}>
          Your feedback is marked afterwards and appears on the attempt, usually within a minute
          or two.
        </p>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function Timing({
  label,
  seconds,
  fallback,
}: {
  label: string;
  seconds: number | null;
  fallback: string;
}) {
  return (
    <li className={`flex items-center gap-2 ${b2cBodyText}`}>
      <HiOutlineClock className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
      <span className="font-medium text-b2c-text-secondary">{label}</span>
      <span>{seconds === null ? fallback : `${Math.round(seconds / 60)} minutes`}</span>
    </li>
  );
}
