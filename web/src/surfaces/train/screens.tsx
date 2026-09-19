"use client";

import type { ScreenMap, ScreenProps } from "@/surfaces/contract";
import { AccessPanel } from "@/capabilities/account";
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
/*
 * "Access" is the account capability's own panel, not a screen of this arm.
 *
 * There were two: this arm had a read-only list of entitlements whose receipts
 * section was broken — `GET /me/receipts` answers receipt *ids* and the screen
 * read fields off them, so every value rendered undefined — while the account
 * capability had the ported one, with the plan picker that actually reaches
 * checkout. Two jobs wrote them at once, neither able to see the other.
 *
 * The capability's survives, and belongs to it: what somebody has bought is
 * about the person, not the arm they are standing in.
 */
const TrainAccess = () => <AccessPanel />;

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
  access: TrainAccess,
};
