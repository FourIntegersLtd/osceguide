"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HiOutlineXMark,
} from "react-icons/hi2";
import {
  Alert,
  Panel,
  Button,
  cn,
  productTokens,
  Spinner,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { useCurrentExam } from "@/foundation/session";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { browseLibrary, type LibraryStation } from "@/capabilities/stations";
import { createSet } from "@/domains/train/api";
import { combineIntro, describeCreateSetFailure, incompleteVersionIds } from "@/domains/train/mocks/model";
import { B2CHero } from "@/foundation/ui/B2CHero";
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
  const { hrefFor, surface } = useSurface();
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
    } catch (cause) {
      setErrorText(describeCreateSetFailure(cause, surface));
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="space-y-6 pb-24">
      <B2CHero title="Build a focused session">
        {combineIntro(incompleteIds.length > 0)}
      </B2CHero>

      {incompleteIds.length === 0 ? null : (
        <form onSubmit={handleCreate} className="max-w-3xl">
          <Panel title="Session details" scrollable={false}>
            <div className="space-y-5">
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
                  placeholder="Name this session"
                />
              </div>

              <div ref={dropdownRef} className="relative">
                <label htmlFor="combine-stations-select-attempted-stations" className={productTokens.b2cFieldLabel}>Search stations</label>
                <input
                  id="combine-stations-select-attempted-stations"
                  type="text"
                  placeholder="Search stations"
                  value={stationSearch}
                  onChange={(event) => setStationSearch(event.target.value)}
                  onFocus={() => setIsDropdownOpen(true)}
                  className={cn(productTokens.b2cInputBase, "mt-1.5")}
                />
                {isDropdownOpen && filteredStations.length > 0 ? (
                  <div className="absolute z-20 mt-1.5 max-h-60 w-full overflow-auto rounded-control border border-b2c-border bg-osce-surface p-1 shadow-[0_8px_24px_rgba(16,24,40,0.08)]">
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
            </div>

            {selected.length > 0 ? (
              <div className="mt-5">
                <p className={productTokens.b2cFieldLabel}>Selected stations ({selected.length})</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {selected.map((station) => (
                    <span
                      key={station.version_id}
                      className="inline-flex h-7 items-center gap-1 rounded-osce-sm bg-b2c-surface-muted pl-2.5 pr-1 text-osce-meta font-medium text-osce-ink-700"
                    >
                      {station.title}
                      <button
                        type="button"
                        onClick={() =>
                          setSelected((prev) =>
                            prev.filter((item) => item.version_id !== station.version_id),
                          )
                        }
                        className="inline-flex h-5 w-5 items-center justify-center rounded text-b2c-text-muted hover:bg-osce-navActive hover:text-osce-ink-900"
                        aria-label={`Remove ${station.title}`}
                      >
                        <HiOutlineXMark className="h-3.5 w-3.5" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            {errorText ? (
              <div className="mt-3">
                <Alert tone="danger">{errorText}</Alert>
              </div>
            ) : null}
            {successMessage ? (
              <div className="mt-3">
                <Alert tone="success">{successMessage}</Alert>
              </div>
            ) : null}

            <div className="mt-5 flex justify-end">
              <Button type="submit" variant="primary" size="md" disabled={isCreating}>
                {isCreating ? <Spinner size="sm" className="text-current" label="Creating" /> : null}
                {isCreating ? "Creating" : "Create session"}
              </Button>
            </div>
          </Panel>
        </form>
      )}
    </div>
  );
}
