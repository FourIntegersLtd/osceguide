"use client";

import { useState, type FormEvent } from "react";
import { LuPlus, LuX } from "react-icons/lu";
import { Alert, AsyncBoundary, B2CPageHeader, Button, ButtonLink, productTokens, Panel } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { LibraryStation } from "@/capabilities/stations";
import { describeRefusal } from "@/capabilities/stations/refusal";
import { useAsync, useToast } from "@/foundation/hooks";
import {
  listSets,
  loadStationCatalogue,
  readSet,
  updateSet,
  type StationSet,
} from "@/domains/train/api";
import {
  attemptedVersionIds,
  chooseStations,
  entriesInOrder,
  sessionUpdatedMessage,
  stationLabel,
} from "@/domains/train/mocks/model";

const { b2cFieldLabel, b2cIconButton, b2cInputBase } = productTokens;

/** A station in the session: the version the set points at, and its title once it has been sat. */
interface SessionStation {
  versionId: string;
  station_title: string | null;
  sat: boolean;
}

function sessionStations(set: StationSet): SessionStation[] {
  return entriesInOrder(set).map((entry) => ({
    versionId: entry.station_version_id,
    station_title: entry.station_title ?? null,
    sat: entry.attempts > 0,
  }));
}

/**
 * The pencil's page (canvas `train-session-edit`).
 *
 * A name field and the session's stations. A station is never chosen by its title or case: that
 * would tell the learner what they are about to sit. "Add a station" picks a random station of the
 * session's exam they have not sat (as `chooseStations` does for a new session), and a station not
 * yet sat can be removed; one already sat cannot (`set_entry_has_attempts`), so it offers no Remove.
 * One PATCH saves the name and the list together.
 */
export function MockUpdate({ setId }: { setId: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      const [catalogue, sets] = await Promise.all([loadStationCatalogue(set.exam_code, signal), listSets(signal)]);
      return { set, catalogue, attempted: attemptedVersionIds(sets.items) };
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
        {({ set, catalogue, attempted }) => (
          <UpdateForm set={set} catalogue={catalogue} attempted={attempted} cancelHref={hrefFor(`/mocks/${setId}`)} />
        )}
      </AsyncBoundary>
    </div>
  );
}

function UpdateForm({
  set,
  catalogue,
  attempted,
  cancelHref,
}: {
  set: StationSet;
  catalogue: readonly LibraryStation[];
  attempted: ReadonlySet<string>;
  cancelHref: string;
}) {
  const toast = useToast();
  const [name, setName] = useState(set.name);
  const [stations, setStations] = useState(() => sessionStations(set));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const inSession = new Set(stations.map((station) => station.versionId));
  const addable = catalogue.filter((station) => !inSession.has(station.version_id));

  const addStation = () => {
    const [picked] = chooseStations(addable, 1, {
      excludeVersionIds: attempted,
    });
    if (!picked) return;
    setStations((previous) => [...previous, { versionId: picked.version_id, station_title: null, sat: false }]);
  };

  const removeStation = (versionId: string) => {
    setStations((previous) => previous.filter((station) => station.versionId !== versionId));
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    try {
      const updated = await updateSet(set.id, {
        name,
        stationVersionIds: stations.map((station) => station.versionId),
      });
      setStations(sessionStations(updated));
      toast.success(sessionUpdatedMessage(updated.total_entries));
    } catch (cause) {
      setError(describeRefusal(cause, "Could not update the session. Try again."));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={(event) => void save(event)} className="max-w-[640px]">
      <Panel title="Session" scrollable={false}>
        <div className="space-y-5">
          {error ? <Alert tone="danger">{error}</Alert> : null}

          <div className="space-y-1.5">
            <label htmlFor="mock_name" className={b2cFieldLabel}>
              Name
            </label>
            <input
              id="mock_name"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={b2cInputBase}
              placeholder="Session name"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className={b2cFieldLabel}>In this session · {stations.length}</h3>
              <Button type="button" variant="secondary" size="sm" onClick={addStation} disabled={addable.length === 0}>
                <LuPlus aria-hidden className="h-4 w-4" />
                Add a station
              </Button>
            </div>
            {stations.length === 0 ? (
              <p className="rounded-osce-lg border border-dashed border-osce-border px-4 py-5 text-center text-osce-meta text-b2c-text-muted">
                No stations yet. Add a station to start.
              </p>
            ) : (
              <ul className="divide-y divide-osce-border-light rounded-osce-lg border border-osce-border">
                {stations.map((station, index) => {
                  const label = stationLabel(station, index);
                  return (
                    <li key={station.versionId} className="flex min-h-[48px] items-center gap-3 pl-3 pr-1">
                      <span className="min-w-0 flex-1 truncate text-osce-body text-osce-ink-900">{label}</span>
                      {station.sat ? (
                        <span className="pr-3 text-osce-meta text-b2c-text-muted">Sat</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => removeStation(station.versionId)}
                          className={b2cIconButton}
                          aria-label={`Remove ${label}`}
                        >
                          <LuX aria-hidden className="h-4 w-4" />
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="flex flex-wrap justify-end gap-2 border-t border-osce-border-light pt-4">
            <ButtonLink href={cancelHref} variant="secondary" size="md">
              Back to session
            </ButtonLink>
            <Button type="submit" disabled={isSaving} isLoading={isSaving}>
              Update session
            </Button>
          </div>
        </div>
      </Panel>
    </form>
  );
}
