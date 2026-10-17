"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineCheck } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  Button,
  Modal,
  StationCompletionProgressBar,
  productTokens,
  Panel,
  Spinner,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { createSet, readSetAllowance } from "@/domains/train/api";
import { AddExamDate } from "@/capabilities/account/AddExamDate";
import { isOrgSurface } from "@/capabilities/surface";
import { UpgradePlans } from "@/domains/train/mocks/SetupPrompts";
import {
  BEFORE_YOU_START,
  attemptedVersionIds,
  chooseStations,
  describeCreateSetFailure,
  nothingPickableMessage,
  pickerMax,
  trialStationsHint,
} from "@/domains/train/mocks/model";
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
 * field: the name is shown as text, not a field (it is not editable by learners), a refusal to create opens the upgrade modal, and a missing
 * exam date is asked for once per browser session.
 *
 * The old backend took the number and picked the stations itself
 * (`customise_mock`). `POST /me/station-sets` takes explicit version ids, so
 * the picking moved here: the client already knows which stations this person
 * has attempted, so a new session prefers unseen ones. On the free trial the count is capped at
 * the stations the trial has left, which the server also enforces (`trial_station_limit`).
 */
export function MockSetup({ workspace, onCreated }: { workspace: MockWorkspace; onCreated: () => void }) {
  const router = useRouter();
  const { hrefFor, surface } = useSurface();
  // An institution's trainee practises what the organisation granted: no trial, no plans.
  const org = isOrgSurface(surface);
  const { session, refresh } = useSession();
  const { code: currentExam } = useCurrentExam();
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
  const allowance = useAsync(
    (signal) => (examCode ? readSetAllowance(examCode, signal) : Promise.resolve({ free_stations_left: null })),
    [examCode],
  );
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
      setError(describeCreateSetFailure(cause, surface));
      // The old backend flagged this refusal with `show_upgrade_modal`.
      setShowUpgradeModal(!org && hasCode(cause, "not_entitled"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full space-y-6 pb-24">
      {org ? null : (
        <StationCompletionProgressBar
          subscriptionExpired={access.subscriptionExpired}
          completedCount={attempted.size}
          totalCount={stations.length}
          hasPaid={access.hasPaid}
          freeLimit={workspace.trial.stations}
        />
      )}

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel title="Session setup">
          <AsyncBoundary state={allowance}>
            {({ free_stations_left: freeStationsLeft }) => {
              const maxStations = pickerMax(stations.length, freeStationsLeft);
              const hint = trialStationsHint(freeStationsLeft, surface);
              return (
                <div className="flex flex-col gap-4">
                  {successMessage ? <Alert tone="success">{successMessage}</Alert> : null}
                  {error ? <Alert tone="danger">{error}</Alert> : null}
                  {nothingPickable ? (
                    <Alert tone="info" title="No stations to build a session from">
                      {nothingPickableMessage({
                        hasPaid: access.hasPaid,
                        subscriptionExpired: access.subscriptionExpired,
                        trial: workspace.trial,
                        surface,
                      })}
                    </Alert>
                  ) : null}

                  <div className="flex flex-col gap-1">
                    <span className={productTokens.b2cFieldLabel}>Session name</span>
                    <p className="text-osce-body font-medium text-osce-ink-900">{name}</p>
                    {/* Hidden for learners: only admins edit or delete sessions (2026-10-14). */}
                    {/* <p className="text-osce-meta text-b2c-text-muted">You can rename it later from your sessions.</p> */}
                  </div>

                  <label htmlFor="requested_station_count" className="flex flex-col gap-1.5">
                    <span className={productTokens.b2cFieldLabel}>Number of stations</span>
                    <input
                      type="number"
                      id="requested_station_count"
                      name="requested_station_count"
                      value={stationCount}
                      onChange={(event) => setStationCount(event.target.value)}
                      min={1}
                      max={maxStations}
                      aria-describedby={hint ? "requested_station_count_hint" : undefined}
                      className={productTokens.b2cInputBase}
                      required
                    />
                    {hint ? (
                      <span id="requested_station_count_hint" className="text-osce-meta text-b2c-text-muted">
                        {hint}
                      </span>
                    ) : null}
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
                        Include previously attempted stations. Practise stations from a previous subscription; leave
                        unchecked for only new stations.
                      </span>
                    </label>
                  ) : null}

                  <div>
                    <Button
                      type="button"
                      variant="primary"
                      size="md"
                      onClick={submit}
                      disabled={isSubmitting || nothingPickable || maxStations === 0}
                    >
                      {isSubmitting ? <Spinner size="sm" className="text-current" label="Starting" /> : null}
                      {isSubmitting ? "Creating" : "Create session"}
                    </Button>
                  </div>
                </div>
              );
            }}
          </AsyncBoundary>
        </Panel>

        <section className="rounded-osce-lg bg-b2c-surface-muted p-6">
          <span className={productTokens.b2cMonoEyebrow}>Before you start</span>
          <ul className="mt-3 flex flex-col gap-2.5">
            {BEFORE_YOU_START.map((item) => (
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
        <Modal width="400px" height="fit-content" title="Add your exam date" onClose={skipExamDate}>
          <AddExamDate
            examDate={null}
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
