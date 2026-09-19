"use client";

import type { ScreenMap, ScreenProps } from "@/surfaces/contract";
import {
  AttemptResult,
  ExamDashboard,
  MockDetail,
  MockStationRunner,
  Mocks,
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

function TrainMockStation({ params }: ScreenProps) {
  return <MockStationRunner setId={params?.setId ?? ""} entryId={params?.entryId ?? ""} />;
}

function TrainAttempt({ params }: ScreenProps) {
  return <AttemptResult attemptId={params?.attemptId ?? ""} />;
}

export const trainScreens: ScreenMap = {
  dashboard: TrainDashboard,
  mocks: TrainMocks,
  mockDetail: TrainMockDetail,
  mockStation: TrainMockStation,
  attempt: TrainAttempt,
};
