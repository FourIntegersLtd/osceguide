"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { HiOutlinePlusCircle } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  Button,
  ConfirmModal,
  PlatformTabbedScreen,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { useCursorPages, useToast, useSearchQuery } from "@/foundation/hooks";
import {
  isMediaKind,
  MEDIA_KIND_LABELS,
  type MediaKind,
} from "@/capabilities/media/api";
import { AuthoringCatalogFilterBar } from "@/capabilities/authoring/parts/AuthoringCatalogFilterBar";
import { AUTHORING_ALL_EXAMS } from "@/capabilities/authoring/parts/examCatalogFilter";
import {
  AUTHORING_MEDIA_PAGE_LIMIT,
  deleteMedia,
  listMediaForAuthoring,
  publishMedia,
  unlockMedia,
  unpublishMedia,
  type MediaItem,
} from "@/capabilities/staff-media/api";
import { MediaListTable } from "@/capabilities/staff-media/MediaListTable";
import { MediaNewModal } from "@/capabilities/staff-media/MediaNewScreen";
import {
  staffMediaDetailPath,
  staffMediaListPath,
} from "@/capabilities/staff-media/paths";
import { useAction } from "@/capabilities/authoring/parts/useAction";

const TABS: B2CSegmentedTabItem<MediaKind>[] = [
  { id: "summary", label: "Summaries" },
  { id: "slide_deck", label: "Slide decks" },
  { id: "blog", label: "Blog" },
  { id: "podcast", label: "Podcast" },
];

const CONFIRM_COPY = {
  publish: {
    title: "Publish this?",
    message: "Learners will see it straight away.",
    confirm: "Publish",
    done: "Published",
  },
  unpublish: {
    title: "Unpublish this?",
    message: "Learners lose it and it goes back to a draft you can edit or delete.",
    confirm: "Unpublish",
    done: "Unpublished",
  },
  unlock: {
    title: "Release this job?",
    message: "Only if the worker has died. The item is marked failed so you can start it again.",
    confirm: "Release",
    done: "Released",
  },
} as const;

export function MediaAuthoringHome() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // The tab lives in the URL, so a reload, a shared link or Back keeps it.
  const rawKind = searchParams.get("kind");
  const kind: MediaKind = rawKind && isMediaKind(rawKind) ? rawKind : "summary";
  const setKind = (next: MediaKind) =>
    router.push(staffMediaListPath(next), { scroll: false });
  const [createOpen, setCreateOpen] = useState(false);
  const [examFilter, setExamFilter] = useState(AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);

  // A page at a time, scoped and searched in SQL. This used to walk every
  // cursor up front and re-filter by exam and search text in the browser.
  const pages = useCursorPages(
    (cursor, signal) =>
      listMediaForAuthoring(
        kind,
        {
          cursor,
          limit: AUTHORING_MEDIA_PAGE_LIMIT,
          examCode: examFilter || null,
          q: query || null,
        },
        signal,
      ),
    [kind, examFilter, query],
  );
  const list = pages.state;

  useEffect(() => {
    setSearch("");
  }, [kind]);

  useEffect(() => {
    if (searchParams.get("new") === "1") setCreateOpen(true);
  }, [searchParams]);

  const closeCreate = () => {
    setCreateOpen(false);
    if (searchParams.get("new") === "1") {
      router.replace(staffMediaListPath(kind));
    }
  };
  const action = useAction(list.reload);
  const toast = useToast();
  // What the person is asked to confirm before anything reaches learners or is taken from them.
  const [confirm, setConfirm] = useState<{
    verb: "publish" | "unpublish" | "unlock";
    item: MediaItem;
  } | null>(null);

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
          <p className="text-osce-body text-ink-muted">
            {visibleCount}
            {pages.hasMore ? "+" : ""}{" "}
            {MEDIA_KIND_LABELS[kind].many.toLowerCase()} in the catalogue.
          </p>
        }
        trailing={
          <Button
            size="sm"
            className="gap-2"
            onClick={() => setCreateOpen(true)}
          >
            <HiOutlinePlusCircle className="h-4 w-4" aria-hidden />
            New {kindLabel.toLowerCase()}
          </Button>
        }
      />

      <MediaNewModal
        open={createOpen}
        initialKind={kind}
        initialExam={examFilter}
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
          <>
            <MediaListTable
              items={list.data ?? []}
              more={pages}
              busy={action.busy}
              onOpen={(item: MediaItem) =>
                router.push(staffMediaDetailPath(item.id))
              }
              onPublish={(item) => setConfirm({ verb: "publish", item })}
              onUnpublish={(item) => setConfirm({ verb: "unpublish", item })}
              onUnlock={(item) => setConfirm({ verb: "unlock", item })}
              onDelete={(item) =>
                void action.run(`delete:${item.id}`, async () => {
                  await deleteMedia(item.id);
                  toast.success("Deleted");
                })
              }
            />
          </>
        )}
      </AsyncBoundary>
      <ConfirmModal
        isOpen={confirm !== null}
        tone={confirm?.verb === "publish" ? "default" : "danger"}
        title={CONFIRM_COPY[confirm?.verb ?? "publish"].title}
        message={`"${confirm?.item.title ?? ""}": ${CONFIRM_COPY[confirm?.verb ?? "publish"].message}`}
        confirmText={CONFIRM_COPY[confirm?.verb ?? "publish"].confirm}
        isLoading={action.busy !== null}
        error={action.error}
        onCancel={() => {
          setConfirm(null);
          action.clearError();
        }}
        onConfirm={() => {
          if (!confirm) return;
          const { verb, item } = confirm;
          const work = { publish: publishMedia, unpublish: unpublishMedia, unlock: unlockMedia }[verb];
          void action
            .run(`${verb}:${item.id}`, async () => {
              await work(item.id);
              toast.success(CONFIRM_COPY[verb].done);
            })
            .then((ok) => {
              if (ok) setConfirm(null);
            });
        }}
      />
    </PlatformTabbedScreen>
  );
}
