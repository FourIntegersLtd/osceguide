"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { HiOutlinePlusCircle } from "react-icons/hi2";
import { Alert, AsyncBoundary, Button, PlatformTabbedScreen, type B2CSegmentedTabItem } from "@/foundation/ui";
import { useAsync, useToast } from "@/foundation/hooks";
import { isMediaKind, MEDIA_KIND_LABELS, type MediaKind } from "@/capabilities/media/api";
import { AuthoringCatalogFilterBar } from "@/capabilities/authoring/parts/AuthoringCatalogFilterBar";
import {
  AUTHORING_ALL_EXAMS,
} from "@/capabilities/authoring/parts/examCatalogFilter";
import {
  deleteMedia,
  listAllMediaForAuthoring,
  publishMedia,
  type MediaItem,
} from "@/capabilities/staff-media/api";
import { MediaListTable } from "@/capabilities/staff-media/MediaListTable";
import { MediaNewModal } from "@/capabilities/staff-media/MediaNewScreen";
import { staffMediaDetailPath } from "@/capabilities/staff-media/paths";
import { useAction } from "@/capabilities/authoring/parts/useAction";

const TABS: B2CSegmentedTabItem<MediaKind>[] = [
  { id: "summary", label: "Summaries" },
  { id: "slide_deck", label: "Slide decks" },
  { id: "blog", label: "Blog" },
  { id: "podcast", label: "Podcast" },
];

export function MediaAuthoringHome() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [kind, setKind] = useState<MediaKind>("summary");
  const [createOpen, setCreateOpen] = useState(false);
  const [examFilter, setExamFilter] = useState(AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  const list = useAsync((signal) => listAllMediaForAuthoring(kind, signal), [kind]);

  useEffect(() => {
    setSearch("");
  }, [kind]);

  useEffect(() => {
    if (searchParams.get("new") === "1") setCreateOpen(true);
  }, [searchParams]);

  const createKind = useMemo(() => {
    const raw = searchParams.get("kind");
    if (raw && isMediaKind(raw)) return raw;
    return kind;
  }, [searchParams, kind]);

  const closeCreate = () => {
    setCreateOpen(false);
    if (searchParams.get("new") === "1") {
      router.replace("/staff/media");
    }
  };
  const action = useAction(list.reload);
  const toast = useToast();

  const kindLabel = MEDIA_KIND_LABELS[kind].one;

  const visibleCount = useMemo(() => list.data?.length ?? 0, [list.data]);

  return (
    <PlatformTabbedScreen
      title="Study material"
      tabs={TABS}
      value={kind}
      onChange={setKind}
      ariaLabel="Material kind"
    >
      <AuthoringCatalogFilterBar
        examCode={examFilter}
        onExamCodeChange={setExamFilter}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search by title or slug…"
        searchAriaLabel="Search study material by title or slug"
        leading={
          <p className="text-osce-body text-b2c-text-muted">
            {visibleCount} {MEDIA_KIND_LABELS[kind].many.toLowerCase()} in the catalogue.
          </p>
        }
        trailing={
          <Button size="sm" className="gap-2" onClick={() => setCreateOpen(true)}>
            <HiOutlinePlusCircle className="h-4 w-4" aria-hidden />
            New {kindLabel.toLowerCase()}
          </Button>
        }
      />

      <MediaNewModal
        open={createOpen}
        initialKind={createKind}
        onClose={closeCreate}
        onCreated={() => {
          list.reload();
        }}
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <AsyncBoundary
        state={list}
        isEmpty={() => (list.data?.length ?? 0) === 0}
        empty={{
          title: `No ${MEDIA_KIND_LABELS[kind].many.toLowerCase()}`,
          description: examFilter
            ? "Nothing matches this exam filter. Try clearing it."
            : "Create one to get started.",
        }}
      >
        {() => (
          <MediaListTable
            items={list.data ?? []}
            examFilter={examFilter}
            search={search}
            busy={action.busy}
            onOpen={(item: MediaItem) => router.push(staffMediaDetailPath(item.id))}
            onPublish={(item) =>
              void action.run(`publish:${item.id}`, async () => {
                await publishMedia(item.id);
                toast.success("Published");
              })
            }
            onDelete={(item) =>
              void action.run(`delete:${item.id}`, async () => {
                await deleteMedia(item.id);
                toast.success("Deleted");
              })
            }
          />
        )}
      </AsyncBoundary>
    </PlatformTabbedScreen>
  );
}
