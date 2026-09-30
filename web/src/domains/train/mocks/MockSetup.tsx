"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineArrowPath, HiOutlineCog6Tooth } from "react-icons/hi2";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  Modal,
  ModalContent,
  ModalPrimaryButton,
  ModalSecondaryButton,
  StationCompletionProgressBar,
  cn,
  productTokens,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { createSet } from "@/domains/train/api";
import { AddExamDate } from "@/domains/train/dashboard/AddExamDate";
import { UpgradePlans } from "@/domains/train/mocks/SetupPrompts";
import { attemptedVersionIds, chooseStations } from "@/domains/train/mocks/model";
import {
  accessState,
  defaultExamCode,
  useExamStations,
  type MockWorkspace,
} from "@/domains/train/mocks/useMockWorkspace";

const FREE_STATION_LIMIT = 3;

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
        setError("An error occurred");
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
      setError(errorMessage(cause));
      // The old backend flagged this refusal with `show_upgrade_modal`.
      setShowUpgradeModal(hasCode(cause, "not_entitled"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-2xl space-y-6 pb-24 lg:w-3/5">
      <StationCompletionProgressBar
        subscriptionExpired={access.subscriptionExpired}
        completedCount={attempted.size}
        totalCount={stations.length}
        hasPaid={access.hasPaid}
        freeLimit={FREE_STATION_LIMIT}
      />

      <ModalContent className="max-w-2xl space-y-3">
        {successMessage ? <Alert tone="success">{successMessage}</Alert> : null}
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader className={productTokens.b2cPanelCardTitle}>
            <HiOutlineCog6Tooth className="h-4 w-4 text-osce-accent" aria-hidden />
            Session setup
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-5">
            <div>
              <label htmlFor="name" className={productTokens.b2cFieldLabel}>
                Session name
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={name}
                readOnly
                disabled
                className={cn(
                  productTokens.b2cInputBase,
                  "mt-1.5",
                  "cursor-not-allowed bg-b2c-surface-muted text-b2c-text-muted",
                )}
                placeholder="Enter a descriptive session name"
                required
              />
            </div>

            <div>
              <label htmlFor="requested_station_count" className={productTokens.b2cFieldLabel}>
                Number of stations
              </label>
              <input
                type="number"
                id="requested_station_count"
                name="requested_station_count"
                value={stationCount}
                onChange={(event) => setStationCount(event.target.value)}
                min={1}
                max={stations.length}
                className={cn(productTokens.b2cInputBase, "mt-1.5")}
                required
              />
            </div>

            {hasLockedSets ? (
              <label
                htmlFor="include_previously_attempted"
                className="flex cursor-pointer items-start gap-3 rounded-md border border-b2c-border bg-b2c-surface-muted px-3 py-3"
              >
                <input
                  type="checkbox"
                  id="include_previously_attempted"
                  name="include_previously_attempted"
                  checked={includePreviouslyAttempted}
                  onChange={(event) => setIncludePreviouslyAttempted(event.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-b2c-border text-osce-accent focus:ring-osce-accent/20"
                />
                <span className="min-w-0">
                  <span className={cn("block", productTokens.b2cGroupedRowTitle)}>
                    Include previously attempted stations
                  </span>
                  <span className={cn("mt-0.5 block", productTokens.b2cBodyTextMuted)}>
                    Enable this to practice stations from a previous subscription. Leave unchecked
                    for only new stations.
                  </span>
                </span>
              </label>
            ) : null}
          </B2CPanelCardBody>
          <B2CPanelCardFooter>
            <ModalSecondaryButton
              type="button"
              onClick={() => router.push(hrefFor("/mocks/list"))}
              className="w-full sm:w-auto"
            >
              View All Sessions
            </ModalSecondaryButton>
            <ModalPrimaryButton
              type="button"
              onClick={submit}
              disabled={isSubmitting}
              className="w-full gap-2 sm:w-auto"
            >
              {isSubmitting ? (
                <>
                  <HiOutlineArrowPath className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                "Create Session"
              )}
            </ModalPrimaryButton>
          </B2CPanelCardFooter>
        </B2CPanelCard>

        {showUpgradeModal ? (
          <Modal width="600px" height="fit-content" onClose={() => setShowUpgradeModal(false)}>
            <UpgradePlans examCode={examCode} />
          </Modal>
        ) : null}
      </ModalContent>

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
