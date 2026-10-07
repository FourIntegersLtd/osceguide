"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineArrowPath, HiOutlineCheck } from "react-icons/hi2";
import { Alert, Button, Modal, StationCompletionProgressBar, cn, productTokens, Panel } from "@/foundation/ui";
import { hasCode } from "@/foundation/platform-client";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { createSet } from "@/domains/train/api";
import { AddExamDate } from "@/domains/train/dashboard/AddExamDate";
import { UpgradePlans } from "@/domains/train/mocks/SetupPrompts";
import { attemptedVersionIds, chooseStations, describeCreateSetFailure, nothingPickableMessage } from "@/domains/train/mocks/model";
import {
  accessState,
  defaultExamCode,
  useExamStations,
  type MockWorkspace,
} from "@/domains/train/mocks/useMockWorkspace";

/** Remembered per session so the exam-date prompt doesn't reopen on every visit. */
const EXAM_DATE_SKIP_KEY = "exam_date_prompt_skipped";

function examDatePromptSkipped(): boolean {
  try {
    return window.sessionStorage.getItem(EXAM_DATE_SKIP_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Session setup: a number of stations, and go.
 *
 * The retiring client's `CustomizeMock` and `CustomiseMockForm`, field for
 * field: the name is shown but not editable (it is renamed afterwards from the
 * sessions list), a refusal to create opens the upgrade modal, and a missing
 * exam date is asked for once per browser session.
 *
 * The old backend took the number and picked the stations itself
 * (`customise_mock`). `POST /me/station-sets` takes explicit version ids, so
 * the picking moved here: the client already knows which stations this person
 * has attempted, so a new session prefers unseen ones.
 */
export function MockSetup({
  workspace,
  onCreated,
}: {
  workspace: MockWorkspace;
  onCreated: () => void;
}) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const { session, refresh } = useSession();
  const { code: currentExam, settings } = useCurrentExam();
  const examCode = defaultExamCode(workspace, currentExam);
  // The old client counted and scanned this exam's sessions only.
  const examSets = useMemo(
    () => workspace.sets.filter((set) => set.exam_code === examCode),
    [workspace.sets, examCode],
  );
  // Kept as typed, so a cleared field stays cleared rather than snapping to 1.
  const [stationCount, setStationCount] = useState("1");
  const [includePreviouslyAttempted, setIncludePreviouslyAttempted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [examDateSkipped, setExamDateSkipped] = useState(examDatePromptSkipped);

  const name = `Session ${examSets.length + 1}`;
  const stations = useExamStations(workspace, examCode);
  const attempted = useMemo(() => attemptedVersionIds(examSets), [examSets]);
  const hasLockedSets = examSets.some((set) => set.locked);
  const access = accessState(workspace, examCode);
  // `chooseStations` falls back to attempted stations, so it is empty only when the exam shows none.
  const nothingPickable = stations.length === 0;
  const missingExamDate = session !== null && !session.user.exam_date;
  const showExamDateModal = missingExamDate && !examDateSkipped;

  const skipExamDate = () => {
    try {
      window.sessionStorage.setItem(EXAM_DATE_SKIP_KEY, "1");
    } catch {
      // A browser that refuses storage just asks again next time.
    }
    setExamDateSkipped(true);
  };

  const submit = async () => {
    setIsSubmitting(true);
    setSuccessMessage("");
    setError("");
    try {
      const picked = chooseStations(stations, Number.parseInt(stationCount, 10) || 0, {
        excludeVersionIds: includePreviouslyAttempted ? undefined : attempted,
      });
      if (picked.length === 0) {
        setError("Enter how many stations you want, at least 1.");
        return;
      }
      const set = await createSet({
        name,
        examCode,
        stationVersionIds: picked.map((station) => station.version_id),
      });
      setSuccessMessage("Session created successfully!");
      onCreated();
      router.push(hrefFor(`/mocks/${set.id}`));
    } catch (cause) {
      setError(describeCreateSetFailure(cause));
      // The old backend flagged this refusal with `show_upgrade_modal`.
      setShowUpgradeModal(hasCode(cause, "not_entitled"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full space-y-6 pb-24">
      <StationCompletionProgressBar
        subscriptionExpired={access.subscriptionExpired}
        completedCount={attempted.size}
        totalCount={stations.length}
        hasPaid={access.hasPaid}
        freeLimit={workspace.trial.stations}
      />

      {access.hasPaid === false && !access.subscriptionExpired ? (
        <p className="text-osce-body text-ink-muted">
          Free trial: {workspace.trial.stations} stations, each up to {workspace.trial.attempts_per_station} times,
          within {workspace.trial.days} days of signing up.
        </p>
      ) : null}

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel title="Session setup">
            <div className="flex flex-col gap-4">
              {successMessage ? <Alert tone="success">{successMessage}</Alert> : null}
              {error ? <Alert tone="danger">{error}</Alert> : null}
              {nothingPickable ? (
                <Alert tone="info" title="No stations to build a session from">
                  {nothingPickableMessage({
                    hasPaid: access.hasPaid,
                    subscriptionExpired: access.subscriptionExpired,
                    trial: workspace.trial,
                  })}
                </Alert>
              ) : null}

              <label htmlFor="name" className="flex flex-col gap-1.5">
                <span className={productTokens.b2cFieldLabel}>Session name</span>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={name}
                  readOnly
                  className={cn(productTokens.b2cInputBase, "bg-b2c-surface-muted text-osce-ink-700")}
                />
              </label>

              <label htmlFor="requested_station_count" className="flex flex-col gap-1.5">
                <span className={productTokens.b2cFieldLabel}>Number of stations</span>
                <input
                  type="number"
                  id="requested_station_count"
                  name="requested_station_count"
                  value={stationCount}
                  onChange={(event) => setStationCount(event.target.value)}
                  min={1}
                  max={stations.length}
                  className={productTokens.b2cInputBase}
                  required
                />
              </label>

              {hasLockedSets ? (
                <label
                  htmlFor="include_previously_attempted"
                  className="flex cursor-pointer items-start gap-2.5 text-osce-body text-osce-ink-700"
                >
                  <input
                    type="checkbox"
                    id="include_previously_attempted"
                    name="include_previously_attempted"
                    checked={includePreviouslyAttempted}
                    onChange={(event) => setIncludePreviouslyAttempted(event.target.checked)}
                    className="mt-0.5 h-4 w-4 shrink-0 rounded border-b2c-border accent-osce-accent"
                  />
                  <span>
                    Include previously attempted stations. Practise stations from a previous
                    subscription; leave unchecked for only new stations.
                  </span>
                </label>
              ) : null}

              <div>
                <Button type="button" variant="primary" size="md" onClick={submit} disabled={isSubmitting || nothingPickable}>
                  {isSubmitting ? <HiOutlineArrowPath className="h-4 w-4 animate-spin" aria-hidden /> : null}
                  {isSubmitting ? "Creating" : "Create session"}
                </Button>
              </div>
            </div>
        </Panel>

        <section className="rounded-osce-lg bg-b2c-surface-muted p-6">
          <span className={productTokens.b2cMonoEyebrow}>Before you start</span>
          <ul className="mt-3 flex flex-col gap-2.5">
            {["A working microphone", "Headphones, to avoid echo", "A quiet room and stable internet"].map((item) => (
              <li key={item} className="flex items-center gap-2.5 text-osce-ink-700">
                <HiOutlineCheck className="h-4 w-4 shrink-0 text-osce-success-icon" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </section>
      </div>

      {showUpgradeModal ? (
        <Modal width="600px" height="fit-content" onClose={() => setShowUpgradeModal(false)}>
          <UpgradePlans examCode={examCode} />
        </Modal>
      ) : null}

      {showExamDateModal ? (
        <Modal
          width="400px"
          height="fit-content"
          title="Add your exam date"
          onClose={skipExamDate}
        >
          <AddExamDate
            examDate={null}
            examTime={null}
            dateLabel={settings.date_label}
            onSaved={() => {
              void refresh();
              setExamDateSkipped(true);
            }}
            onSkip={skipExamDate}
          />
        </Modal>
      ) : null}
    </div>
  );
}
