"use client";

import { HiOutlineClipboardDocumentList, HiOutlinePlay } from "react-icons/hi2";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  Button,
  ButtonLink,
  cn,
  productTokens,
} from "@/foundation/ui";
import { useMicPreflight } from "@/foundation/livekit";
import { useSurface } from "@/capabilities";
import type { Exam } from "@/capabilities/stations";
import type { SetEntry, StationSet } from "@/domains/train/api";
import { sessionMinutes } from "@/domains/train/mocks/model";

/**
 * What happens next, before the clock starts.
 *
 * Every number on this screen is the exam's — reading length, consultation
 * length, how many attempts a station allows. The retiring client kept eight
 * constants in `constants.ts` (`SCA_DOCTOR_TIMER_DURATION` and its siblings)
 * and a hardcoded `ALLOWED_STATION_ATTEMPTS = 3`, which meant an exam whose
 * timings changed on the backend went on advertising the old ones here.
 */
export function MockRules({
  set,
  entry,
  exam,
}: {
  set: StationSet;
  entry: SetEntry | null;
  exam: Exam | null;
}) {
  const { hrefFor } = useSurface();
  const mic = useMicPreflight();
  const micReady = mic.status === "ready";

  const doctorMinutes = (exam?.default_reading_seconds ?? 180) / 60;
  const simulationMinutes = (exam?.default_simulation_seconds ?? 720) / 60;
  const attemptLimit = exam?.station_attempt_limit ?? 3;
  const duration = sessionMinutes(
    set.total_entries,
    exam
      ? {
          readingSeconds: exam.default_reading_seconds,
          simulationSeconds: exam.default_simulation_seconds,
        }
      : null,
  );

  const rules = [
    {
      highlight: true,
      text: `This session will take ${duration} minutes to complete. for each station, you get ${doctorMinutes.toFixed(1)} minutes for reading the doctor information, followed by ${simulationMinutes.toFixed(1)} minutes for each simulation.`,
    },
    {
      highlight: false,
      text: "You'll hold a spoken consultation with an AI patient, so you need a working microphone. Headphones are recommended to avoid echo.",
    },
    {
      highlight: false,
      text: "Each station follows a structured format. You'll get a warning about halfway through as a cue to move from history taking to management.",
    },
    {
      highlight: false,
      text: "Find a quiet space with stable internet before starting. If you have technical issues, flag the station and contact support through the messages tab.",
    },
    {
      highlight: false,
      text: `You get a maximum of ${attemptLimit} attempts for each station.`,
    },
    {
      highlight: true,
      text: "The timer begins immediately after clicking Start Session. Good luck!",
    },
  ];

  return (
    <div className="mb-12 w-full space-y-6 lg:w-4/6">
      <B2CPanelCard>
        <B2CPanelCardHeader>
          <HiOutlineClipboardDocumentList className="h-4 w-4 text-osce-accent" aria-hidden />
          Rules
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-3">
          <ul className="space-y-3">
            {rules.map((rule) => (
              <li
                key={rule.text}
                className={cn(
                  "rounded-lg border px-4 py-3 text-osce-body leading-relaxed",
                  rule.highlight
                    ? cn(
                        productTokens.b2cReadingTones.practice.card,
                        productTokens.b2cReadingTones.practice.body,
                      )
                    : cn(
                        productTokens.b2cMutedBand,
                        "border-b2c-border text-b2c-text-secondary",
                      ),
                )}
              >
                {rule.text}
              </li>
            ))}
          </ul>
        </B2CPanelCardBody>
      </B2CPanelCard>

      {mic.message ? <Alert tone="warning">{mic.message}</Alert> : null}

      {entry === null ? (
        <Alert tone="warning">This session has no stations in it yet.</Alert>
      ) : micReady ? (
        <ButtonLink
          href={hrefFor(`/mocks/${set.id}/stations/${entry.id}`)}
          variant="commit"
          size="hero"
          fullWidth
          className="inline-flex items-center justify-center gap-2 text-center"
        >
          <HiOutlinePlay className="h-4 w-4" aria-hidden />
          Start Session
        </ButtonLink>
      ) : (
        <Button
          type="button"
          variant="commit"
          size="hero"
          fullWidth
          onClick={() => void mic.request()}
          className="inline-flex items-center justify-center gap-2 text-center"
        >
          <HiOutlinePlay className="h-4 w-4" aria-hidden />
          Allow your microphone to start
        </Button>
      )}
    </div>
  );
}
