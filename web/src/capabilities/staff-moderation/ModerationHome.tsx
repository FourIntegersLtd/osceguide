"use client";

import { useState } from "react";
import {
  AsyncBoundary,
  Button,
  ConfirmModal,
  Panel,
  PlatformPageHeader,
  Row,
  RowList,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  deleteModerationPost,
  listModerationPosts,
  type ModerationPost,
} from "@/capabilities/staff-moderation/api";

function formatDay(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function ModerationHome() {
  const state = useAsync(
    (signal) => listModerationPosts({ days: 7 }, signal),
    [],
  );
  const toast = useToast();
  const [target, setTarget] = useState<ModerationPost | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmDelete = async () => {
    if (!target) return;
    setBusy(true);
    setError(null);
    try {
      await deleteModerationPost(target.id);
      toast.success("Post removed");
      setTarget(null);
      state.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Moderation"
        description="Recent community posts. Remove anything that should not stay public."
      />

      <Panel title="Last seven days" padding="none">
        <AsyncBoundary
          state={state}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: "Queue is empty",
            description: "No posts in the last seven days.",
            bare: true,
          }}
        >
          {(page) => (
            <RowList flush>
              {page.items.map((post) => (
                <Row key={post.id} className="items-start">
                  <div className="min-w-0 flex-1">
                    <p className="text-osce-data font-medium text-ink">
                      {"title" in post &&
                      typeof post.title === "string" &&
                      post.title
                        ? post.title
                        : post.kind === "reply"
                          ? "Reply"
                          : "Post"}
                    </p>
                    <p className="mt-0.5 text-osce-meta text-ink-subtle">
                      {formatDay(post.created_at)}
                    </p>
                    <p className="mt-2 line-clamp-3 text-osce-body text-ink-muted">
                      {post.body}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setTarget(post)}
                  >
                    Delete
                  </Button>
                </Row>
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Panel>

      <ConfirmModal
        isOpen={target !== null}
        onCancel={() => {
          setTarget(null);
          setError(null);
        }}
        onConfirm={() => void confirmDelete()}
        isLoading={busy}
        error={error}
        tone="danger"
        title="Delete this post?"
        confirmText="Delete"
        message="This removes the post for everyone. It cannot be undone from here."
      />
    </div>
  );
}
