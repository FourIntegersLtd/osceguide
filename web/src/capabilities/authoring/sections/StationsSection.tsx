"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { importLabel, stationsLead } from "@/capabilities/authoring/lib/authoringCopy";
import { AuthoringConfirm } from "@/capabilities/authoring/parts/AuthoringConfirm";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { HiOutlineCloudArrowUp, HiOutlinePlusCircle } from "react-icons/hi2";
import { useSurface } from "@/capabilities";
import { isPlatformAdmin, useSession } from "@/foundation/session";
import {
  matchesStatusFilter,
  parseStatusFilter,
  stationListUrl,
  type StationStatusFilter,
} from "@/capabilities/authoring/parts/stationListUrl";
import { stationNewPath } from "@/capabilities/authoring/stations/paths";
import { Alert } from "@/foundation/ui";
import { AuthoringLeadButton } from "@/capabilities/authoring/parts/AuthoringLeadButton";
import { boardStack } from "@/capabilities/authoring/parts/boardUi";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { AuthoringCatalogFilterBar } from "@/capabilities/authoring/parts/AuthoringCatalogFilterBar";
import { AuthoringSectionLead } from "@/capabilities/authoring/parts/AuthoringSectionLead";
import {
  AUTHORING_ALL_EXAMS,
  matchesExamFilter,
} from "@/capabilities/authoring/parts/examCatalogFilter";
import { useAsync, useCursorPages, useSearchQuery } from "@/foundation/hooks";
import {
  archiveStationVersion,
  listStations,
  setStationApproval,
  listStationTemplates,
  STATION_PAGE_LIMIT,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ImportStationDialog } from "@/capabilities/authoring/imports/ImportStationDialog";
import { StationDetail } from "@/capabilities/authoring/sections/StationDetail";
import { StationsTable } from "@/capabilities/authoring/sections/StationsTable";
import { StationUsedBy } from "@/capabilities/authoring/sections/StationUsedBy";

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
  const w = useAssessWords();
  const org = !useAuthoringChrome().b2c;
  const { session } = useSession();
  const router = useRouter();
  const { hrefFor } = useSurface();
  const searchParams = useSearchParams();
  // An exam page links here with its code.
  const [examFilter, setExamFilter] = useState(searchParams.get("exam") ?? AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);
  // The status filter and the open station live in the address, so a reload or a shared
  // link lands on the same list, and a saved station has an address of its own.
  const pathname = usePathname();
  const status = parseStatusFilter(searchParams.get("status"));
  const openId = searchParams.get("station");
  // Arriving on a station's own address, it may be an archived one; the filter alone would hide it.
  const [deepLinked] = useState(openId !== null);
  const includeArchived = status !== "active" || deepLinked;
  const goTo = (next: { status: StationStatusFilter; station?: string | null }) =>
    router.replace(stationListUrl(pathname, next), { scroll: false });
  const [importing, setImporting] = useState(false);
  const [archiveConfirm, setArchiveConfirm] = useState<{
    id: string;
    title: string;
    version: number;
  } | null>(null);

  // A page at a time, searched and exam-filtered in SQL. This used to walk up
  // to 25 pages of 100 before drawing anything, and quietly stopped at 2,500
  // stations. Changing the exam filter is in `deps`, so it restarts from page
  // one rather than re-filtering whatever happened to be loaded already.
  const pages = useCursorPages(
    (cursor, signal) =>
      listStations(
        scope,
        {
          cursor,
          limit: STATION_PAGE_LIMIT,
          search: query,
          exam_code: examFilter || undefined,
          // The server leaves archived out unless asked.
          include_archived: includeArchived,
        },
        signal,
      ).then((page) => ({
        ...page,
        items: page.items.filter((item) => deepLinked || matchesStatusFilter(item.status, status)),
      })),
    [scope.base, query, examFilter, status, deepLinked],
  );
  const stations = pages.state;
  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);
  const action = useAction(stations.reload);

  // The server already excludes archived stations and matches the exam
  // filter, so this is just the length of what came back.
  const open = openId ? (stations.data?.find((s) => s.id === openId) ?? null) : null;
  // The station is on a later page than the first: keep reading until it turns up.
  useEffect(() => {
    if (openId && !open && pages.hasMore && !pages.loadingMore) pages.loadMore();
  }, [openId, open, pages]);
  const visibleCount = stations.data?.length ?? 0;

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
          goTo({ status });
          stations.reload();
        }}
      />
    );
  }

  return (
    <div className={org ? boardStack : "space-y-4"}>
      <AuthoringSectionLead
        action={
          <>
            <AuthoringLeadButton icon={HiOutlineCloudArrowUp} onClick={() => setImporting(true)}>
              {importLabel(w)}
            </AuthoringLeadButton>
            <AuthoringLeadButton primary icon={HiOutlinePlusCircle} onClick={() => router.push(stationNewPath(hrefFor))}>
              New station
            </AuthoringLeadButton>
          </>
        }
      >
        {stationsLead(w)}
        {stations.data ? (
          <span className={org ? "block text-assess-label font-bold text-ink" : "block text-osce-data font-normal text-ink-muted"}>
            {visibleCount}
            {pages.hasMore ? "+" : ""} station{visibleCount === 1 && !pages.hasMore ? "" : "s"}
            {published.length > 0 ? ` · ${published.length} template${published.length === 1 ? "" : "s"} available` : ""}
          </span>
        ) : null}
      </AuthoringSectionLead>

      <AuthoringCatalogFilterBar
        examCode={examFilter}
        onExamCodeChange={setExamFilter}
        search={search}
        onSearchChange={setSearch}
        status={status}
        onStatusChange={(next) => goTo({ status: next })}
        searchPlaceholder="Search stations by name…"
        searchAriaLabel="Search stations"
      />

      {action.error && archiveConfirm === null ? <Alert tone="danger">{action.error}</Alert> : null}
      {stations.error ? (
        <Alert tone="danger">
          Could not load stations. {stations.error.message}
          <button type="button" className="ml-2 underline" onClick={() => stations.reload()}>
            Retry
          </button>
        </Alert>
      ) : null}

      {stations.loading && !stations.data ? (
        <p className="text-osce-body text-ink-muted" role="status">Loading stations…</p>
      ) : (
        <StationsTable
          stations={stations.data ?? []}
          more={pages}
          search={query}
          busy={action.busy}
          onOpen={(station) => goTo({ status, station: station.id })}
          showApproval={scope.kind === "platform"}
          onToggleApproval={
            scope.kind === "platform" && isPlatformAdmin(session)
              ? (station) =>
                  void action.run(`approval:${station.id}`, () =>
                    setStationApproval(scope, station.id, !station.approved),
                  )
              : undefined
          }
          onArchive={(station) =>
            setArchiveConfirm({
              id: station.id,
              title: station.title,
              version: station.version,
            })
          }
        />
      )}

      <ImportStationDialog
        open={importing}
        onClose={() => setImporting(false)}
        onChanged={() => {
          stations.reload();
          templates.reload();
        }}
      />

      <AuthoringConfirm
        isOpen={archiveConfirm !== null}
        onCancel={() => {
          if (action.busy) return;
          action.clearError();
          setArchiveConfirm(null);
        }}
        error={action.error}
        onConfirm={() => {
          if (!archiveConfirm) return;
          const { id, version } = archiveConfirm;
          void action
            .run(`archive:${id}`, () => archiveStationVersion(scope, id, version, w))
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
        tone="danger"
        message={
          <>
            {archiveConfirm ? (
              <StationUsedBy stationId={archiveConfirm.id} version={archiveConfirm.version} />
            ) : null}
            <span className="mt-1 block">
              Past attempts stay intact. The station is removed from the live library.
            </span>
          </>
        }
      />
    </div>
  );
}

export function hasPublishedVersion(template: StationTemplate): boolean {
  return template.versions.some((v) => v.status === "published");
}
