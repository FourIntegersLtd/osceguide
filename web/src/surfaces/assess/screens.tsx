"use client";

import type { ScreenMap, ScreenProps } from "@/surfaces/contract";
import {
  MockDetail,
  MockEnd,
  MockList,
  MockUpdate,
  Mocks,
  SetStation,
} from "@/domains/train";
import {
  stationActionFromParam,
  stationStepFromParam,
} from "@/capabilities/station-runner/useStationUrl";
import {
  CircuitRunner,
  EditCircuit,
  LiveBoard,
  MySittingDetail,
  MyResult,
  NewCircuit,
  NewSitting,
  OrgDashboard,
  Results,
  SelfPractice,
  SelfPracticeStation,
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

function AssessCircuitEdit(props: ScreenProps) {
  return <EditCircuit orgSlug={slugOf(props)} circuitId={props.params?.circuitId ?? ""} />;
}

function AssessResults(props: ScreenProps) {
  return <Results orgSlug={slugOf(props)} sittingId={props.params?.sittingId ?? ""} />;
}

function AssessSlotReview(props: ScreenProps) {
  return (
    <SlotReview
      orgSlug={slugOf(props)}
      slotId={props.params?.slotId ?? ""}
      attemptId={props.params?.attemptId || null}
    />
  );
}

function AssessTrainees(props: ScreenProps) {
  return <Trainees orgSlug={slugOf(props)} />;
}

function AssessTeam(props: ScreenProps) {
  return <Team orgSlug={slugOf(props)} />;
}

function AssessMyTraining({ params }: ScreenProps) {
  return <TraineeHome slotId={params?.slot || null} />;
}

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

function AssessPracticeStation({ params, workspace }: ScreenProps) {
  const orgSlug = workspace.orgSlug ?? "";
  return (
    <SelfPracticeStation
      orgSlug={orgSlug}
      stationId={params?.stationId ?? ""}
      action={stationActionFromParam(params?.action)}
      step={stationStepFromParam(params?.tab)}
      attemptId={params?.attempt || null}
    />
  );
}

/*
 * Practice sets, answered on this arm by Train's screens.
 *
 * A set belongs to the person sitting it: `/me/station-sets` is unscoped, so an
 * institution workspace asks the identical question and gets the identical
 * answer. Adapting four components is cheaper than a second implementation that
 * can drift, and the alternative — an institution trainee reduced to one
 * station at a time — is what shipped until now. `mocks` is the whole of why
 * these are here; the other three are the set's own detail, station and end.
 */
const AssessMocks = () => <Mocks />;

function AssessMockDetail({ params }: ScreenProps) {
  return <MockDetail setId={params?.setId ?? ""} />;
}

function AssessMockStation({ params }: ScreenProps) {
  return (
    <SetStation
      setId={params?.setId ?? ""}
      entryId={params?.entryId ?? ""}
      action={stationActionFromParam(params?.action)}
      step={stationStepFromParam(params?.tab)}
      attemptId={params?.attempt || null}
    />
  );
}

function AssessMockComplete({ params }: ScreenProps) {
  return <MockEnd setId={params?.setId ?? ""} />;
}

const AssessMockList = () => <MockList />;

function AssessMockUpdate({ params }: ScreenProps) {
  return <MockUpdate setId={params?.setId ?? ""} />;
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
  circuitEdit: AssessCircuitEdit,
  live: AssessLiveBoard,
  sittingResults: AssessResults,
  slotReview: AssessSlotReview,
  trainees: AssessTrainees,
  team: AssessTeam,
  myTraining: AssessMyTraining,
  mySitting: AssessMySitting,
  myResult: AssessMyResult,
  myPractice: AssessMyPractice,
  mocks: AssessMocks,
  mockDetail: AssessMockDetail,
  mockStation: AssessMockStation,
  mockComplete: AssessMockComplete,
  mockList: AssessMockList,
  mockUpdate: AssessMockUpdate,
  attempt: AssessAttempt,
  practiceStation: AssessPracticeStation,
};
