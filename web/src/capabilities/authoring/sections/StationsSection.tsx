"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlinePlusCircle } from "react-icons/hi2";
import { useSurface } from "@/capabilities";
import { stationNewPath } from "@/capabilities/authoring/stations/paths";
import { Alert, ConfirmModal } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { AuthoringCatalogFilterBar } from "@/capabilities/authoring/parts/AuthoringCatalogFilterBar";
import { AuthoringSectionLead } from "@/capabilities/authoring/parts/AuthoringSectionLead";
import {
  AUTHORING_ALL_EXAMS,
  matchesExamFilter,
} from "@/capabilities/authoring/parts/examCatalogFilter";
import { useAsync } from "@/foundation/hooks";
import {
  archiveStationVersion,
  listAllStations,
  listStationTemplates,
  type Station,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { StationDetail } from "@/capabilities/authoring/sections/StationDetail";
import { StationsTable } from "@/capabilities/authoring/sections/StationsTable";

/**
 * The station catalogue, and the way into one station's versions.
 *
 * The retiring client had three of these — the institution's flat list, the
 * partner's list grouped by exam, and the platform admin's — differing in
 * their header and in nothing else. The table matches the B2C admin station
 * list; exam filter stays in the bar above it.
 */
export function StationsSection() {
  const scope = useAuthoringScope();
  const router = useRouter();
  const { hrefFor } = useSurface();
  const [examFilter, setExamFilter] = useState(AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<Station | null>(null);
  const [archiveConfirm, setArchiveConfirm] = useState<{
    id: string;
    title: string;
    version: number;
  } | null>(null);

  const stations = useAsync((signal) => listAllStations(scope, signal), [scope.base]);
  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);
  const action = useAction(stations.reload);

  const visibleCount = useMemo(() => {
    const items = stations.data ?? [];
    return items.filter(
      (s) => s.status !== "archived" && matchesExamFilter(s.exam_code, examFilter),
    ).length;
  }, [stations.data, examFilter]);

  const published = useMemo(() => {
    const all = (templates.data?.items ?? []).filter(hasPublishedVersion);
    if (!examFilter) return all;
    return all.filter((t) => matchesExamFilter(t.exam_code, examFilter, { includeUnscoped: true }));
  }, [templates.data, examFilter]);

  if (open) {
    return (
      <StationDetail
        station={open}
        templates={templates.data?.items ?? []}
        onBack={() => {
          setOpen(null);
          stations.reload();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <AuthoringSectionLead
        action={
          <AuthoringButton
            variant="commit"
            size="sm"
            className="gap-2"
            onClick={() => router.push(stationNewPath(hrefFor))}
          >
            <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
            New station
          </AuthoringButton>
        }
      >
        Published station cases for sessions and practice.
        {stations.data ? (
          <span className="block text-sm font-normal text-b2c-text-secondary">
            {visibleCount} station{visibleCount === 1 ? "" : "s"}
            {published.length > 0 ? ` · ${published.length} template(s) available` : ""}
          </span>
        ) : null}
      </AuthoringSectionLead>

      <AuthoringCatalogFilterBar
        examCode={examFilter}
        onExamCodeChange={setExamFilter}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search stations by name…"
        searchAriaLabel="Search stations"
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
      {stations.error ? (
        <Alert tone="danger">
          {stations.error.message}
          <button type="button" className="ml-2 underline" onClick={() => stations.reload()}>
            Retry
          </button>
        </Alert>
      ) : null}

      {stations.loading && !stations.data ? (
        <p className="text-osce-body text-b2c-text-secondary" role="status">Loading stations…</p>
      ) : (
        <StationsTable
          stations={stations.data ?? []}
          examFilter={examFilter}
          search={search}
          busy={action.busy}
          onOpen={setOpen}
          onArchive={(station) =>
            setArchiveConfirm({
              id: station.id,
              title: station.title,
              version: station.version,
            })
          }
        />
      )}

      <ConfirmModal
        isOpen={archiveConfirm !== null}
        onCancel={() => {
          if (!action.busy) setArchiveConfirm(null);
        }}
        onConfirm={() => {
          if (!archiveConfirm) return;
          const { id, version } = archiveConfirm;
          void action
            .run(`archive:${id}`, () => archiveStationVersion(scope, id, version))
            .then((ok) => {
              if (ok) setArchiveConfirm(null);
            });
        }}
        isLoading={archiveConfirm !== null && action.busy === `archive:${archiveConfirm.id}`}
        title={
          archiveConfirm
            ? `Archive "${archiveConfirm.title}" (v${archiveConfirm.version})?`
            : "Archive station?"
        }
        confirmText="Archive"
        message="Past attempts stay intact. The station is removed from the live library."
      />
    </div>
  );
}

export function hasPublishedVersion(template: StationTemplate): boolean {
  return template.versions.some((v) => v.status === "published");
}
