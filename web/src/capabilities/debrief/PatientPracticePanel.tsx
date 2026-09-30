"use client";

import { useCallback, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { BarVisualizer, useConnectionState, useVoiceAssistant } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { HiOutlinePhoneXMark } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  AthenaIdentity,
  ATHENA_IMAGE_SRC,
  Button,
  cn,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { AGENT_STATE_LABEL, VoiceRoom, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { isPlatformError } from "@/foundation/platform-client";
import LivekitIdleState from "@/foundation/livekit/LivekitIdleState";
import { useSurface } from "@/capabilities";
import { assistantSurfaceFor } from "@/capabilities/surface";
import { parsePatientIdentity } from "@/capabilities/attempt-runner/consultation/patientIdentity";
import { readAttemptReview, type AttemptBrief, type AttemptReview } from "@/capabilities/attempt-runner";
import { PatientRoleplayScript } from "@/capabilities/debrief/PatientRoleplayScript";
import {
  sectionLines,
  sectionsFor,
  type AudienceSection,
} from "@/capabilities/attempt-runner/material/AudienceSections";
import {
  athenaDoctorVoiceToken,
  startAthenaDoctorSession,
  readPatientRoleplay,
} from "@/capabilities/debrief/api";

const { b2cLivekitEndButton } = productTokens;

export function PatientPracticePanel({
  attemptId,
  examCode,
  brief,
  review: initialReview,
}: {
  attemptId: string;
  examCode: string;
  brief: AttemptBrief | null;
  review: AttemptReview | null;
}) {
  const reviewState = useAsync((signal) => readAttemptReview(attemptId, signal), [attemptId]);
  const script = useAsync((signal) => readPatientRoleplay(attemptId, signal), [attemptId]);
  const review = initialReview ?? reviewState.data ?? null;
  const stationTitle = review?.station_title ?? brief?.station_title ?? null;
  const patientBiodata = brief?.patient.name_line ?? null;
  const patientGender = brief?.patient.gender ?? null;

  return (
    <div className="grid grid-cols-1 overflow-hidden rounded-lg border border-b2c-border lg:grid-cols-5 lg:h-[min(620px,calc(90dvh-11rem))]">
      <div className="flex max-h-[min(50dvh,420px)] min-h-0 flex-col overflow-hidden border-b border-b2c-border lg:col-span-3 lg:max-h-none lg:border-b-0 lg:border-r">
        <AsyncBoundary state={script}>
          {(patient) => (
            <PatientRoleplayScript sections={patient.sections ?? []} subtitle={patientBiodata} noBorder />
          )}
        </AsyncBoundary>
      </div>
      <div className="min-h-[22rem] min-w-0 bg-b2c-surface-muted p-4 lg:col-span-2 lg:min-h-0 sm:p-5">
        {reviewState.error && !initialReview ? (
          <Alert tone="warning" className="mb-3">
            {errorMessage(reviewState.error)}
          </Alert>
        ) : null}
        <AthenaDoctorVoicePanel
          attemptId={attemptId}
          examCode={examCode}
          stationId={review?.station_id ?? brief?.station_id ?? null}
          stationTitle={stationTitle}
          patientBiodata={patientBiodata}
          patientGender={patientGender}
          brief={brief}
          review={review}
          patientSections={script.data?.sections ?? []}
        />
      </div>
    </div>
  );
}

function AthenaDoctorVoicePanel({
  attemptId,
  examCode,
  stationId,
  stationTitle,
  patientBiodata,
  patientGender,
  brief,
  review,
  patientSections,
}: {
  attemptId: string;
  examCode: string;
  stationId: string | null;
  stationTitle: string | null;
  patientBiodata: string | null;
  patientGender: string | null;
  brief: AttemptBrief | null;
  review: AttemptReview | null;
  patientSections: AudienceSection[];
}) {
  const { surface } = useSurface();
  const pathname = usePathname();
  const toast = useToast();
  const mic = useMicPreflight();
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [starting, setStarting] = useState(false);
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const patient = useMemo(
    () => parsePatientIdentity(patientBiodata ?? undefined, patientGender ?? undefined),
    [patientBiodata, patientGender],
  );

  const startVoice = useCallback(async () => {
    setStarting(true);
    setError(null);
    try {
      if (mic.status !== "ready" && !await mic.request()) return;
      const session = await startAthenaDoctorSession({
        attemptId,
        examCode,
        stationId,
        stationTitle,
        patientName: patient.name,
        patientGender,
        patientBiodata,
        // The template's sections as `Label: text` lines, whichever exam wrote them.
        patientInformation: sectionLines(sectionsFor(brief?.sections ?? [], "candidate")),
        ice: sectionLines(sectionsFor(patientSections, "patient")),
        managementPoints: sectionLines(sectionsFor(review?.sections ?? [], "examiner")).slice(0, 24),
      }, {
        surface: assistantSurfaceFor(surface),
        route: pathname ?? "",
      });
      setGrant(await athenaDoctorVoiceToken(session.id));
    } catch (cause) {
      setGrant(null);
      const next = cause instanceof Error ? cause : new Error(String(cause));
      setError(next);
      toast.show({
        tone: "error",
        title: "We couldn't start Athena Doctor",
        message: isPlatformError(next) ? next.message : "Please check your microphone and try again.",
      });
    } finally {
      setStarting(false);
    }
  }, [
    attemptId,
    brief,
    examCode,
    mic,
    patient.name,
    patientBiodata,
    patientGender,
    pathname,
    stationId,
    stationTitle,
    surface,
    toast,
    review,
    patientSections,
  ]);

  const endVoice = useCallback(() => { setGrant(null); setEnded(true); }, []);
  const patientLabel = patient.name ? `Consulting you as ${patient.name}` : "Consulting you as the patient";

  return (
    <div className="mx-auto flex h-full min-h-0 w-full max-w-sm flex-col justify-center gap-4">
      {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
      {mic.message && <Alert tone="warning">{mic.message}</Alert>}

      {grant ? (
        <VoiceRoom grant={grant} onDisconnected={() => endVoice()} onError={setError}>
          <DoctorLiveStage onEnd={endVoice} />
        </VoiceRoom>
      ) : (
        <div className="flex min-h-0 flex-col items-center justify-center text-center">
          <LivekitIdleState
            avatar={{ kind: "image", src: ATHENA_IMAGE_SRC, alt: "Athena" }}
            title="Athena Doctor"
            subtitle={patientLabel}
            className="mb-6"
          />
          <Button
            type="button"
            fullWidth
            onClick={() => void startVoice()}
            disabled={starting || ended || !stationId}
            isLoading={starting}
            className="gap-2"
          >
            {starting ? "Connecting..." : !stationId ? "Loading station..." : "Start consultation"}
          </Button>
        </div>
      )}
    </div>
  );
}

function DoctorLiveStage({ onEnd }: { onEnd: () => void }) {
  const { state, audioTrack } = useVoiceAssistant();
  const connectionState = useConnectionState();
  const connecting =
    connectionState === ConnectionState.Connecting ||
    connectionState === ConnectionState.Reconnecting ||
    connectionState === ConnectionState.SignalReconnecting;
  const agentLabel =
    state === "disconnected" && connectionState !== ConnectionState.Connected
      ? ""
      : (AGENT_STATE_LABEL[state] ?? state);

  return (
    <div className="flex h-full min-h-0 flex-col items-center justify-between gap-5 py-2">
      <div className="flex w-full flex-1 flex-col items-center justify-center">
        <AthenaIdentity title="Athena Doctor" description="Demonstrating the consultation" />
        <div className="mt-5 h-24 w-full max-w-sm rounded-xl border border-osce-accent-subtle bg-osce-surface px-4 py-3">
          <BarVisualizer
            state={state}
            barCount={5}
            trackRef={audioTrack}
            style={{
              height: "100%",
              opacity: state === "disconnected" ? 0.5 : 1,
              transition: "all 0.3s ease",
            }}
          />
        </div>
        <p
          role="status"
          aria-live="polite"
          className="mt-3 text-center text-osce-body font-extralight tracking-wide text-b2c-text-secondary"
        >
          {agentLabel}
        </p>
      </div>

      {connecting ? (
        <Button type="button" fullWidth disabled isLoading className="gap-2">
          Connecting…
        </Button>
      ) : (
        <button type="button" className={cn(b2cLivekitEndButton, "w-full gap-2")} onClick={onEnd}>
          <HiOutlinePhoneXMark className="h-4 w-4 sm:h-5 sm:w-5" aria-hidden />
          <span>End consultation</span>
        </button>
      )}
    </div>
  );
}
