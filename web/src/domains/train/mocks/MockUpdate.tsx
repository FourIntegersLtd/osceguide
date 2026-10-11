"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { HiOutlineMagnifyingGlass, HiOutlineXMark } from "react-icons/hi2";
import Alert from "@/foundation/forms/Alert";
import { AsyncBoundary, B2CPageHeader, Button, ButtonLink, cn, productTokens, Panel } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { errorMessage, useAsync, useSearchQuery } from "@/foundation/hooks";
import { browseLibrary } from "@/capabilities/stations";
import { readSet, updateSet, type StationSet } from "@/domains/train/api";
import { entriesInOrder } from "@/domains/train/mocks/model";

const { b2cFieldLabel, b2cIconButton, b2cInputBase } = productTokens;

/** How many stations the search list shows at once. Typing narrows it on the server. */
const SEARCH_RESULTS_LIMIT = 25;
/** The most station titles one request may ask for. */
const TITLES_LIMIT = 100;

/** A station as this page lists it: the version the set points at, and its title. */
interface PickableStation {
  versionId: string;
  name: string;
}

/**
 * The pencil's page (canvas `train-session-edit`): the retiring client's
 * `UpdateMock`, control for control.
 *
 * A name field, a search box that asks the server for stations of the session's
 * exam matching what was typed, and the chosen stations with a remove button
 * each. One PATCH saves the name and the list together.
 */
export function MockUpdate({ setId }: { setId: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      // Only the titles of the stations already in the session, not the whole library.
      const entries = entriesInOrder(set);
      const chosen =
        entries.length > 0
          ? await browseLibrary(
              {
                examCode: set.exam_code,
                versionIds: entries.map((entry) => entry.station_version_id),
                limit: TITLES_LIMIT,
              },
              signal,
            )
          : { items: [] };
      const titles = new Map(chosen.items.map((station) => [station.version_id, station.title]));
      const selected: PickableStation[] = entries.map((entry) => ({
        versionId: entry.station_version_id,
        name: titles.get(entry.station_version_id) ?? "Station",
      }));
      return { set, selected };
    },
    [setId],
  );

  return (
    <div className="space-y-6">
      <B2CPageHeader
        back={{ href: hrefFor(`/mocks/${setId}`), label: "Session" }}
        title="Update session"
        subtitle="Change the session name and add or remove stations."
      />
      <AsyncBoundary state={state}>
        {({ set, selected }) => (
          <UpdateForm
            set={set}
            initialStations={selected}
            cancelHref={hrefFor(`/mocks/${setId}`)}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function UpdateForm({
  set,
  initialStations,
  cancelHref,
}: {
  set: StationSet;
  initialStations: PickableStation[];
  cancelHref: string;
}) {
  const [mockName, setMockName] = useState(set.name);
  const [currentMockStations, setCurrentMockStations] = useState(initialStations);
  const [stationSearch, setStationSearch] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [isUpdatingMock, setIsUpdatingMock] = useState(false);
  const [updatedMock, setUpdatedMock] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");

  // The list closes when a click lands anywhere outside the search box and it.
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && event.target instanceof Node && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedIds = new Set(currentMockStations.map((station) => station.versionId));
  // What the server is asked for: the box, once typing pauses. The match is
  // made in the database, so a station is found however large the library is.
  const query = useSearchQuery(stationSearch);
  const matches = useAsync(
    (signal) => browseLibrary({ examCode: set.exam_code, search: query, limit: SEARCH_RESULTS_LIMIT }, signal),
    [set.exam_code, query],
  );
  const searchedStations: PickableStation[] = (matches.data?.items ?? [])
    .filter((station) => station.title.length > 0 && !selectedIds.has(station.version_id))
    .map((station) => ({ versionId: station.version_id, name: station.title }));

  const handleStationSelect = (station: PickableStation) => {
    setCurrentMockStations((previous) => [...previous, station]);
    setStationSearch("");
  };

  const handleRemoveStation = (versionId: string) => {
    setCurrentMockStations((previous) => previous.filter((station) => station.versionId !== versionId));
  };

  const handleUpdateMock = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsUpdatingMock(true);
    setUpdatedMock(false);
    setSuccessMessage("");
    setError("");
    try {
      await updateSet(set.id, {
        name: mockName,
        stationVersionIds: currentMockStations.map((station) => station.versionId),
      });
      setUpdatedMock(true);
      setSuccessMessage("Session updated.");
    } catch (cause) {
      setError(errorMessage(cause) || "Could not update the session. Try again.");
    } finally {
      setIsUpdatingMock(false);
    }
  };

  return (
    <form onSubmit={(event) => void handleUpdateMock(event)} className="max-w-[640px]">
      <Panel title="Session" scrollable={false}>
        <div className="space-y-5">
          {successMessage && <Alert message={successMessage} type="success" />}
          {error && <Alert message={error} type="error" />}

          <div className="space-y-1.5">
            <label htmlFor="mock_name" className={b2cFieldLabel}>
              Name
            </label>
            <input
              id="mock_name"
              required
              value={mockName}
              onChange={(event) => setMockName(event.target.value)}
              className={b2cInputBase}
              placeholder="Session name"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="station_search" className={b2cFieldLabel}>
              Add stations
            </label>
            <div className="relative" ref={dropdownRef}>
              <HiOutlineMagnifyingGlass
                aria-hidden
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-b2c-text-muted"
              />
              <input
                id="station_search"
                type="text"
                placeholder="Search stations"
                value={stationSearch}
                onChange={(event) => setStationSearch(event.target.value)}
                onFocus={() => setIsDropdownOpen(true)}
                className={cn(b2cInputBase, "pl-9")}
              />

              {isDropdownOpen && (
                <div className="absolute z-10 mt-1.5 max-h-60 w-full overflow-auto rounded-osce-lg border border-osce-border bg-osce-surface py-1 shadow-lg">
                  {searchedStations.length > 0 ? (
                    searchedStations.map((station) => (
                      <button
                        key={station.versionId}
                        type="button"
                        className="block w-full px-3 py-2 text-left text-osce-body text-osce-ink-900 transition-colors hover:bg-b2c-surface-muted"
                        onClick={() => handleStationSelect(station)}
                      >
                        {station.name}
                      </button>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-osce-body text-b2c-text-muted">No stations found</div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-1.5">
            <h3 className={b2cFieldLabel}>
              In this session · {currentMockStations.length}
            </h3>
            {currentMockStations.length === 0 ? (
              <p className="rounded-osce-lg border border-dashed border-osce-border px-4 py-5 text-center text-osce-meta text-b2c-text-muted">
                No stations yet. Search above to add some.
              </p>
            ) : (
              <ul className="divide-y divide-osce-border-light rounded-osce-lg border border-osce-border">
                {currentMockStations.map((station, index) => (
                  <li key={station.versionId} className="flex min-h-[48px] items-center gap-3 pl-3 pr-1">
                    <span className="w-5 shrink-0 font-mono text-osce-meta tabular-nums text-b2c-text-muted">
                      {index + 1}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-osce-body text-osce-ink-900">
                      {station.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleRemoveStation(station.versionId)}
                      className={b2cIconButton}
                      aria-label={`Remove ${station.name}`}
                    >
                      <HiOutlineXMark aria-hidden className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex flex-wrap justify-end gap-2 border-t border-osce-border-light pt-4">
            <ButtonLink href={cancelHref} variant="secondary" size="md">
              {updatedMock ? "Back to session" : "Cancel"}
            </ButtonLink>
            <Button type="submit" disabled={isUpdatingMock || updatedMock} isLoading={isUpdatingMock}>
              {updatedMock ? "Updated" : "Update session"}
            </Button>
          </div>
        </div>
      </Panel>
    </form>
  );
}
