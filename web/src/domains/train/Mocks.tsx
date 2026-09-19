"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Card, Input, PageHeader } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { StationLibrary, type LibraryStation } from "@/capabilities/stations";
import { createSet, listSets } from "@/domains/train/api";

/**
 * Mocks: a personal set of stations to work through.
 *
 * Deliberately not a circuit. A set is re-attemptable and locks when access
 * lapses rather than being deleted, so the work reappears on renewal; a
 * circuit slot is one-shot and scheduled by somebody else.
 */
export function Mocks() {
  const { hrefFor } = useSurface();
  const [building, setBuilding] = useState(false);
  const state = useAsync((signal) => listSets(signal), []);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Your mocks"
        description="Sets of stations you have put together to work through."
        actions={
          <Button onClick={() => setBuilding((open) => !open)}>
            {building ? "Cancel" : "Build a mock"}
          </Button>
        }
      />

      {building && (
        <MockBuilder
          onCreated={() => {
            setBuilding(false);
            state.reload();
          }}
        />
      )}

      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No mocks yet",
          description: "Build one from the station library and work through it at your own pace.",
        }}
      >
        {(page) => (
          <ul className="grid gap-3 sm:grid-cols-2">
            {page.items.map((set) => (
              <li key={set.id}>
                <Link
                  href={hrefFor(`/mocks/${set.id}`)}
                  className="flex h-full flex-col gap-2 rounded-panel border border-border bg-surface p-4 hover:border-border-strong"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-semibold text-ink">{set.name}</h3>
                    <Badge tone={set.locked ? "warning" : "accent"}>
                      {set.locked ? "Locked" : set.exam_code.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-sm text-ink-muted">
                    {set.attempted_entries} of {set.total_entries} attempted
                  </p>
                  <Progress done={set.attempted_entries} total={set.total_entries} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </AsyncBoundary>
    </div>
  );
}

function Progress({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <div
      className="h-1.5 w-full overflow-hidden rounded-full bg-surface-raised"
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
    </div>
  );
}

function MockBuilder({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [picked, setPicked] = useState<LibraryStation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const pick = useCallback((station: LibraryStation) => {
    setPicked((current) =>
      current.some((item) => item.version_id === station.version_id)
        ? current
        : [...current, station],
    );
  }, []);

  const save = useCallback(async () => {
    const examCode = picked[0]?.exam_code;
    if (!examCode) return;
    setBusy(true);
    setError(null);
    try {
      await createSet({
        name: name.trim() || "Untitled mock",
        examCode,
        stationVersionIds: picked.map((station) => station.version_id),
      });
      onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [name, picked, onCreated]);

  return (
    <Card title="Build a mock">
      <div className="flex flex-col gap-4">
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        <Input
          label="Name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Friday morning practice"
        />

        {picked.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-ink">{picked.length} stations</p>
            <ul className="flex flex-wrap gap-2">
              {picked.map((station) => (
                <li key={station.version_id}>
                  <button
                    type="button"
                    onClick={() =>
                      setPicked((current) =>
                        current.filter((item) => item.version_id !== station.version_id),
                      )
                    }
                    className="rounded-full border border-border px-3 py-1 text-sm text-ink-muted hover:border-danger hover:text-danger"
                  >
                    {station.title} ×
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <StationLibrary
          onPick={pick}
          pickLabel="Add"
          selectedVersionIds={new Set(picked.map((station) => station.version_id))}
        />

        <div className="flex justify-end">
          <Button onClick={save} disabled={busy || picked.length === 0}>
            Create mock
          </Button>
        </div>
      </div>
    </Card>
  );
}
