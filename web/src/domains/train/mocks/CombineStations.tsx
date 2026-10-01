"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HiOutlineArrowPath,
  HiOutlineSquare3Stack3D,
  HiOutlineXCircle,
} from "react-icons/hi2";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  Button,
  ModalCallout,
  ModalContent,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
  cn,
  productTokens,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { useCurrentExam } from "@/foundation/session";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { browseLibrary, type LibraryStation } from "@/capabilities/stations";
import { createSet } from "@/domains/train/api";
import { incompleteVersionIds } from "@/domains/train/mocks/model";
import {
  defaultExamCode,
  examByCode,
  type MockWorkspace,
} from "@/domains/train/mocks/useMockWorkspace";

/** A page at a time from the server, once typing pauses. */
const COMBINE_STATIONS_PAGE_LIMIT = 25;

/**
 * Build a focused session out of stations you started and did not finish, in
 * the exam you are sitting: the retiring client's `CombineMockStations`.
 *
 * The old client asked the backend which stations those were
 * (`/api/attempted_incomplete_stations`). The set list already carries every
 * entry with its attempt count, so the question is answered from what is
 * already loaded — and it stays right for a station whose attempts ran out in
 * one session but not another, which the endpoint got wrong.
 */
export function CombineStations({ workspace }: { workspace: MockWorkspace }) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const { code: currentExam } = useCurrentExam();
  const examCode = defaultExamCode(workspace, currentExam);
  const [mockName, setMockName] = useState("");
  const [selected, setSelected] = useState<LibraryStation[]>([]);
  const [stationSearch, setStationSearch] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // The station versions worth combining: started, not yet exhausted, in the
  // exam the person is sitting. A set carries every entry with its attempt
  // count already, so this is a filter over what `workspace` loaded rather
  // than a round trip.
  const incompleteIds = useMemo(() => {
    const limit = examByCode(workspace, examCode)?.station_attempt_limit ?? 3;
    const examSets = workspace.sets.filter((set) => set.exam_code === examCode);
    return incompleteVersionIds(examSets, limit);
  }, [workspace, examCode]);

  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(stationSearch);
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Narrowed to the incomplete version ids and searched in SQL. An empty
  // `incompleteIds` is never sent as a filter — `browseLibrary` reads that as
  // "no restriction" and would hand back the whole library — so the dropdown
  // simply has nothing to page while there is nothing to combine.
  const pages = useCursorPages(
    (cursor, signal) =>
      incompleteIds.length > 0
        ? browseLibrary(
            { examCode, versionIds: incompleteIds, search: query, cursor, limit: COMBINE_STATIONS_PAGE_LIMIT },
            signal,
          )
        : Promise.resolve({ items: [], next_cursor: null }),
    [examCode, incompleteIds.join(","), query],
  );
  const stationResults = pages.state.data ?? [];
  const filteredStations = stationResults.filter(
    (station) => !selected.some((item) => item.version_id === station.version_id),
  );

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selected.length === 0) {
      setErrorText("Select at least one attempted station.");
      return;
    }
    setIsCreating(true);
    setErrorText(null);
    try {
      await createSet({
        name: mockName,
        examCode,
        stationVersionIds: selected.map((station) => station.version_id),
      });
      setMockName("");
      setSelected([]);
      setSuccessMessage("Combined session created successfully");
      window.setTimeout(() => {
        router.push(hrefFor("/mocks/list"));
      }, 700);
    } catch {
      setErrorText("Error creating mock");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <ModalContent className="max-w-2xl space-y-3 pb-24">
      <div>
        <ModalTitle>Combine Attempted Stations</ModalTitle>
        <ModalHelper>
          Create a focused practice session by combining stations you have attempted across several
          mocks.
        </ModalHelper>
      </div>

      {incompleteIds.length === 0 ? (
        <ModalCallout label="Note" className="mt-0">
          This feature becomes available after you attempt some mocks. You can then create a custom
          session from stations you have already tried.
        </ModalCallout>
      ) : (
        <form onSubmit={handleCreate} className="space-y-3">
          <B2CPanelCard className="mt-0">
            <B2CPanelCardHeader>
              <HiOutlineSquare3Stack3D className="h-4 w-4 text-osce-accent" aria-hidden />
              Session details
            </B2CPanelCardHeader>
            <B2CPanelCardBody className="space-y-5">
              <div>
                <label htmlFor="mock_name" className={productTokens.b2cFieldLabel}>
                  Session name
                </label>
                <input
                  id="mock_name"
                  required
                  value={mockName}
                  onChange={(event) => setMockName(event.target.value)}
                  className={cn(productTokens.b2cInputBase, "mt-1.5")}
                  placeholder="Enter session name"
                />
              </div>

              <div ref={dropdownRef} className="relative">
                <label htmlFor="combine-stations-select-attempted-stations" className={productTokens.b2cFieldLabel}>Select attempted stations</label>
                <input
                  id="combine-stations-select-attempted-stations"
                  type="text"
                  placeholder="Search stations..."
                  value={stationSearch}
                  onChange={(event) => setStationSearch(event.target.value)}
                  onFocus={() => setIsDropdownOpen(true)}
                  className={cn(productTokens.b2cInputBase, "mt-1.5")}
                />
                {isDropdownOpen && filteredStations.length > 0 ? (
                  <div className="absolute z-10 mt-1.5 max-h-60 w-full overflow-auto rounded-md border border-b2c-border bg-osce-surface">
                    {filteredStations.map((station) => (
                      <button
                        key={station.version_id}
                        type="button"
                        className={productTokens.b2cDropdownItem}
                        onClick={() => {
                          setSelected((prev) => [...prev, station]);
                          setStationSearch("");
                          setIsDropdownOpen(false);
                        }}
                      >
                        {station.title}
                      </button>
                    ))}
                    {pages.moreError ? (
                      <Alert tone="danger">Could not load more: {pages.moreError.message}</Alert>
                    ) : null}
                    {pages.hasMore ? (
                      <div className="flex justify-center p-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          disabled={pages.loadingMore}
                          onClick={pages.loadMore}
                        >
                          {pages.loadingMore ? "Loading…" : "Load more"}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </B2CPanelCardBody>

            {selected.length > 0 ? (
              <div className="border-t border-b2c-border">
                <div className={productTokens.b2cPanelSubheader}>
                  Selected stations ({selected.length})
                </div>
                <div className="divide-y divide-b2c-border">
                  {selected.map((station) => (
                    <div
                      key={station.version_id}
                      className="flex items-center justify-between gap-3 px-4 py-3"
                    >
                      <span className="min-w-0 text-osce-body text-osce-ink-900">
                        {station.title}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setSelected((prev) =>
                            prev.filter((item) => item.version_id !== station.version_id),
                          )
                        }
                        className="shrink-0 text-b2c-text-muted transition hover:text-osce-danger"
                        aria-label={`Remove ${station.title}`}
                      >
                        <HiOutlineXCircle className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {errorText ? (
              <div className="border-t border-b2c-border px-4 pt-3">
                <Alert tone="danger">{errorText}</Alert>
              </div>
            ) : null}
            {successMessage ? (
              <div className="border-t border-b2c-border px-4 pt-3">
                <Alert tone="success">{successMessage}</Alert>
              </div>
            ) : null}

            <B2CPanelCardFooter>
              <ModalPrimaryButton type="submit" disabled={isCreating} className="gap-2">
                {isCreating ? (
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
        </form>
      )}
    </ModalContent>
  );
}
