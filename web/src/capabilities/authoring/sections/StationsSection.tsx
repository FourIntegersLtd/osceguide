"use client";

import { useMemo, useState } from "react";
import { HiMagnifyingGlass, HiOutlinePlusCircle } from "react-icons/hi2";
import { Button, Card, getInputClassName } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  listStations,
  listStationTemplates,
  type Station,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { CreateStationDialog } from "@/capabilities/authoring/sections/CreateStationDialog";
import { StationDetail } from "@/capabilities/authoring/sections/StationDetail";

/**
 * The station catalogue, and the way into one station's versions.
 *
 * The retiring client had three of these — the institution's flat list, the
 * partner's list grouped by exam, and the platform admin's — differing in
 * their header and in nothing else. This is the flat list, filtered client
 * side because `GET …/stations` has no `q`: the search box is the old screen's
 * and a gap would be a worse answer than filtering the page we already hold.
 */
export function StationsSection() {
  const scope = useAuthoringScope();
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState<Station | null>(null);

  const stations = useAsync(
    (signal) => listStations(scope, { limit: 100 }, signal),
    [scope.base],
  );
  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);

  const rows = useMemo(() => {
    const items = stations.data?.items ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.exam_code.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q),
    );
  }, [stations.data, search]);

  const published = useMemo(
    () => (templates.data?.items ?? []).filter(hasPublishedVersion),
    [templates.data],
  );

  if (open) {
    return (
      <StationDetail
        station={open}
        onBack={() => {
          setOpen(null);
          stations.reload();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-osce-body text-b2b-mid">
          Published station cases for sessions and practice.
        </p>
        <Button
          themeType="b2b"
          variant="commit"
          size="sm"
          className="gap-2"
          disabled={published.length === 0}
          onClick={() => setCreating(true)}
        >
          <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
          New station
        </Button>
      </div>

      <Card themeType="b2b" padding="none" className="overflow-hidden">
        <div className="border-b border-b2b-border px-4 py-3 sm:px-5">
          <div className="relative">
            <HiMagnifyingGlass
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-b2b-mid/60"
              aria-hidden
            />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search stations by title, exam, or ID…"
              aria-label="Search stations"
              className={`${getInputClassName()} pl-9`}
            />
          </div>
        </div>
      </Card>

      <ListCard
        count={rows.length}
        countLabel="Stations"
        meta={`Templates available: ${published.length}`}
        loading={stations.loading && !stations.data}
        error={stations.error ? stations.error.message : null}
        onDismissError={stations.reload}
        empty={{
          title: search ? "No matching stations" : "No stations yet",
          description: search
            ? `Nothing matched "${search}". Try a different search.`
            : published.length > 0
              ? "Create a station from one of your published templates."
              : "Publish a station template first, then add stations here.",
        }}
      >
        {rows.map((station) => (
          <StationRow key={station.id} station={station} onOpen={() => setOpen(station)} />
        ))}
      </ListCard>

      <CreateStationDialog
        open={creating}
        templates={published}
        onClose={() => setCreating(false)}
        onCreated={() => {
          setCreating(false);
          stations.reload();
        }}
      />
    </div>
  );
}

function StationRow({ station, onOpen }: { station: Station; onOpen: () => void }) {
  return (
    <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
      <div className="min-w-0 flex-1">
        <p className="truncate text-osce-body font-medium text-b2b-headline">{station.title}</p>
        <p className="mt-0.5 truncate text-osce-caption text-b2b-mid" title={`Station ID: ${station.id}`}>
          {station.exam_code} · v{station.version}
          {station.owner_kind === "platform" ? " · OSCE Guide" : ""}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <StatusBadge status={station.status} />
        <Button themeType="b2b" variant="secondary" size="xs" onClick={onOpen}>
          Versions
        </Button>
      </div>
    </div>
  );
}

export function hasPublishedVersion(template: StationTemplate): boolean {
  return template.versions.some((v) => v.status === "published");
}
