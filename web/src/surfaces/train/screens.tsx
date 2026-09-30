"use client";

import type { ScreenMap, ScreenProps } from "@/surfaces/contract";
import {
  stationActionFromParam,
  stationStepFromParam,
} from "@/capabilities/station-runner/useStationUrl";
import {
  AttemptLanding,
  ExamDashboard,
  MockDetail,
  MockEnd,
  MockList,
  MockUpdate,
  Mocks,
  PracticeStation,
  SetStation,
} from "@/domains/train";

/**
 * The consumer arm's screens, given the one shape every arm-owned screen has.
 *
 * The screens themselves keep their own prop lists — `{ setId, entryId }` says
 * more at the point of use than `params` does — so the adapting happens here,
 * once per arm, rather than pushing a route-shaped type down into the domain.
 */

const TrainDashboard = () => <ExamDashboard />;
const TrainMocks = () => <Mocks />;

function TrainMockDetail({ params }: ScreenProps) {
  return <MockDetail setId={params?.setId ?? ""} />;
}

/**
 * One station, in whichever of its four steps the URL names.
 *
 * `action`, `tab` and `attempt` come off the query string rather than the
 * path: the retiring client addressed the reading, the consultation, the
 * management plan and the feedback as one screen, and a link to "the feedback
 * for the attempt I sat on Tuesday" is what that shape buys.
 */
function TrainMockStation({ params }: ScreenProps) {
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

function TrainMockComplete({ params }: ScreenProps) {
  return <MockEnd setId={params?.setId ?? ""} />;
}

const TrainMockList = () => <MockList />;

function TrainMockUpdate({ params }: ScreenProps) {
  return <MockUpdate setId={params?.setId ?? ""} />;
}

function TrainPracticeStation({ params }: ScreenProps) {
  return (
    <PracticeStation
      stationId={params?.stationId ?? ""}
      action={stationActionFromParam(params?.action)}
      step={stationStepFromParam(params?.tab)}
      attemptId={params?.attempt || null}
    />
  );
}

/**
 * An attempt reached by its own id, from a link rather than from its station.
 *
 * Its station is where it is actually read, so this finds that and sends them
 * on — which is also what makes a feedback-ready link work months later.
 */
function TrainAttempt({ params }: ScreenProps) {
  return <AttemptLanding attemptId={params?.attemptId ?? ""} />;
}

export const trainScreens: ScreenMap = {
  dashboard: TrainDashboard,
  mocks: TrainMocks,
  mockDetail: TrainMockDetail,
  mockStation: TrainMockStation,
  mockComplete: TrainMockComplete,
  mockList: TrainMockList,
  mockUpdate: TrainMockUpdate,
  practiceStation: TrainPracticeStation,
  attempt: TrainAttempt,
};
