"use client";

import type { ScreenMap, ScreenProps } from "@/surfaces/contract";
import {
  CircuitRunner,
  LiveBoard,
  MySittingDetail,
  MyResult,
  NewCircuit,
  NewSitting,
  OrgDashboard,
  Results,
  SelfPractice,
  SittingDetail,
  Sittings,
  SlotReview,
  StationRecord,
  Team,
  TraineeHome,
  Trainees,
} from "@/domains/assess";

/**
 * The institution arm's screens.
 *
 * Every one of these needs the organisation's slug, which comes from the
 * workspace rather than from the URL being parsed twice. A personal workspace
 * never reaches here: `surfaceForWorkspace` would have chosen Train.
 */

const slugOf = ({ workspace }: ScreenProps) => workspace.orgSlug ?? "";

function AssessDashboard(props: ScreenProps) {
  return <OrgDashboard orgSlug={slugOf(props)} />;
}

function AssessSittings(props: ScreenProps) {
  return <Sittings orgSlug={slugOf(props)} />;
}

function AssessSittingDetail(props: ScreenProps) {
  return <SittingDetail orgSlug={slugOf(props)} sittingId={props.params?.sittingId ?? ""} />;
}

function AssessNewSitting(props: ScreenProps) {
  return <NewSitting orgSlug={slugOf(props)} />;
}

function AssessNewCircuit(props: ScreenProps) {
  return <NewCircuit orgSlug={slugOf(props)} sittingId={props.params?.sittingId ?? ""} />;
}

function AssessLiveBoard(props: ScreenProps) {
  return <LiveBoard orgSlug={slugOf(props)} />;
}

function AssessCircuitRunner(props: ScreenProps) {
  return <CircuitRunner orgSlug={slugOf(props)} circuitId={props.params?.circuitId ?? ""} />;
}

function AssessResults(props: ScreenProps) {
  return <Results orgSlug={slugOf(props)} sittingId={props.params?.sittingId ?? ""} />;
}

function AssessSlotReview(props: ScreenProps) {
  return (
    <SlotReview
      orgSlug={slugOf(props)}
      slotId={props.params?.slotId ?? ""}
      attemptId={props.params?.attemptId ?? null}
    />
  );
}

function AssessTrainees(props: ScreenProps) {
  return <Trainees orgSlug={slugOf(props)} />;
}

function AssessTeam(props: ScreenProps) {
  return <Team orgSlug={slugOf(props)} />;
}

const AssessMyTraining = () => <TraineeHome />;

function AssessMySitting({ params }: ScreenProps) {
  return <MySittingDetail sittingId={params?.sittingId ?? ""} />;
}

function AssessMyResult({ params }: ScreenProps) {
  return <MyResult sittingId={params?.sittingId ?? ""} />;
}

function AssessMyPractice(props: ScreenProps) {
  return <SelfPractice orgSlug={slugOf(props)} />;
}

function AssessAttempt({ params }: ScreenProps) {
  return <StationRecord attemptId={params?.attemptId ?? ""} />;
}

/**
 * Borrowed wholesale by Hire, which declares `screensFrom: "assess"`.
 *
 * An employer is an organisation running an exam-mode sitting, so these are
 * the screens. One object, referenced twice, rather than two maps that drift.
 */
export const assessScreens: ScreenMap = {
  dashboard: AssessDashboard,
  sittings: AssessSittings,
  sittingDetail: AssessSittingDetail,
  newSitting: AssessNewSitting,
  newCircuit: AssessNewCircuit,
  circuitConsole: AssessCircuitRunner,
  live: AssessLiveBoard,
  sittingResults: AssessResults,
  slotReview: AssessSlotReview,
  trainees: AssessTrainees,
  team: AssessTeam,
  myTraining: AssessMyTraining,
  mySitting: AssessMySitting,
  myResult: AssessMyResult,
  myPractice: AssessMyPractice,
  attempt: AssessAttempt,
};
