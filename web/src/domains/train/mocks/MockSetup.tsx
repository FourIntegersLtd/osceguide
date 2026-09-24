"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineArrowPath, HiOutlineCog6Tooth } from "react-icons/hi2";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalContent,
  ModalPrimaryButton,
  ModalSecondaryButton,
  StationCompletionProgressBar,
  cn,
  productTokens,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { useCurrentExam } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { createSet } from "@/domains/train/api";
import { attemptedVersionIds, chooseStations } from "@/domains/train/mocks/model";
import {
  accessState,
  defaultExamCode,
  useExamStations,
  type MockWorkspace,
} from "@/domains/train/mocks/useMockWorkspace";

const FREE_STATION_LIMIT = 3;

/**
 * Session setup: a name, a number of stations, and go.
 *
 * The old backend took the number and picked the stations itself
 * (`customise_mock`). `POST /me/station-sets` takes explicit version ids, so
 * the picking moved here — which is an improvement rather than a workaround:
 * the client already knows which stations this person has attempted, so a new
 * session prefers unseen ones without the backend having to keep a per-user
 * exclusion list.
 */
export function MockSetup({
  workspace,
  onCreated,
  onViewSessions,
}: {
  workspace: MockWorkspace;
  onCreated: () => void;
  onViewSessions: () => void;
}) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  // The exam is the app's. It used to be a dropdown over every exam this
  // person had stations for, which in practice meant the whole catalogue.
  const { code: currentExam } = useCurrentExam();
  const examCode = defaultExamCode(workspace, currentExam);
  const [name, setName] = useState(`Session ${workspace.sets.length + 1}`);
  const [stationCount, setStationCount] = useState(1);
  const [includePreviouslyAttempted, setIncludePreviouslyAttempted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [needsUpgrade, setNeedsUpgrade] = useState(false);

  const stations = useExamStations(workspace, examCode);
  const attempted = useMemo(() => attemptedVersionIds(workspace.sets), [workspace.sets]);
  const hasLockedSets = workspace.sets.some((set) => set.locked);
  const access = accessState(workspace, examCode);
  const submit = async () => {
    const picked = chooseStations(stations, stationCount, {
      excludeVersionIds: includePreviouslyAttempted ? undefined : attempted,
    });
    setSuccessMessage("");
    if (picked.length === 0) {
      setError("There are no stations to put in this session yet.");
      setNeedsUpgrade(false);
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setNeedsUpgrade(false);
    try {
      const set = await createSet({
        name: name.trim() || "Untitled session",
        examCode,
        stationVersionIds: picked.map((station) => station.version_id),
      });
      setSuccessMessage("Session created successfully!");
      onCreated();
      router.push(hrefFor(`/mocks/${set.id}`));
    } catch (cause) {
      // A lapsed or unpurchased plan answers `not_entitled` here, and the
      // retiring client opened its upgrade modal on exactly this refusal. A
      // sentence with nowhere to act on it is worse than the modal was.
      if (hasCode(cause, "not_entitled")) {
        setNeedsUpgrade(true);
        setError("Your access to this exam has ended.");
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-2xl space-y-6 pb-24">
      <StationCompletionProgressBar
        subscriptionExpired={access.subscriptionExpired}
        completedCount={attempted.size}
        totalCount={stations.length}
        hasPaid={access.hasPaid}
        freeLimit={FREE_STATION_LIMIT}
      />

      <ModalContent className="max-w-2xl space-y-3">
        {successMessage ? <Alert tone="success">{successMessage}</Alert> : null}
        {error ? (
          <Alert tone="danger">
            {error}
            {needsUpgrade ? (
              <>
                {" "}
                <Link
                  href={`${hrefFor("/settings")}?tab=payments`}
                  className="font-semibold underline"
                >
                  Renew your plan
                </Link>{" "}
                to keep practising.
              </>
            ) : null}
          </Alert>
        ) : null}

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
                onChange={(event) => setName(event.target.value)}
                className={cn(productTokens.b2cInputBase, "mt-1.5")}
                placeholder="Enter a descriptive session name"
                required
              />
            </div>


            <div>
              <label
                htmlFor="requested_station_count"
                className={productTokens.b2cFieldLabel}
              >
                Number of stations
              </label>
              <input
                type="number"
                id="requested_station_count"
                name="requested_station_count"
                value={stationCount}
                onChange={(event) => setStationCount(Number.parseInt(event.target.value, 10) || 1)}
                min={1}
                max={Math.max(stations.length, 1)}
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
              onClick={onViewSessions}
              className="w-full sm:w-auto"
            >
              View All Sessions
            </ModalSecondaryButton>
            <ModalPrimaryButton
              type="button"
              onClick={submit}
              disabled={isSubmitting || stations.length === 0}
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
      </ModalContent>
    </div>
  );
}
