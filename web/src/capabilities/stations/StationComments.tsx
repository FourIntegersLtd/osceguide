"use client";

import { useCallback, useState } from "react";
import { HiOutlineChatBubbleLeftRight } from "react-icons/hi2";
import { LuHeart } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  B2CPanelCardHeaderIcon,
  Button,
} from "@/foundation/ui";
import { b2cBodyText, b2cBodyTextMuted, b2cInputBase } from "@/foundation/ui/productTokens";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { commentOnStation, listStationComments } from "@/capabilities/stations/api";

/**
 * What other candidates made of this station.
 *
 * `orgId` is the arm's to supply — the same shape `OrgDiscussion` uses — so an
 * institution's trainees discuss a station inside their own organisation while
 * a personal workspace posts to the public board. The capability itself knows
 * only that an audience exists; who may read it is the backend's answer, and
 * the old client's habit of deciding visibility in the browser is what let a
 * cohort's thread leak onto the public board.
 */
export function StationComments({
  stationId,
  orgId = null,
}: {
  stationId: string;
  orgId?: string | null;
}) {
  const state = useAsync((signal) => listStationComments(stationId, signal), [stationId]);

  return (
    <B2CPanelCard>
      <B2CPanelCardHeader>
        <B2CPanelCardHeaderIcon icon={HiOutlineChatBubbleLeftRight} tone="violet" />
        Discussion
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-5">
        <Composer stationId={stationId} orgId={orgId} onPosted={state.reload} />

        <AsyncBoundary
          state={state}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: "No comments yet",
            description: orgId
              ? "Comments from people in your organisation will appear here."
              : "Be the first to say how you found this station.",
          }}
        >
          {(page) => (
            <ul className="space-y-3">
              {page.items.map((comment) => (
                <li
                  key={comment.id}
                  className="rounded-osce-md border border-b2c-border bg-b2c-surface-muted px-4 py-3"
                >
                  <p className={`whitespace-pre-wrap break-words ${b2cBodyText}`}>
                    {comment.body}
                  </p>
                  <div className={`mt-2 flex items-center gap-3 ${b2cBodyTextMuted}`}>
                    <span>{new Date(comment.created_at).toLocaleDateString()}</span>
                    {comment.like_count > 0 && (
                      <span className="inline-flex items-center gap-1">
                        <LuHeart className="h-3.5 w-3.5" aria-hidden />
                        {comment.like_count}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </AsyncBoundary>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function Composer({
  stationId,
  orgId,
  onPosted,
}: {
  stationId: string;
  orgId: string | null;
  onPosted: () => void;
}) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(async () => {
    const text = body.trim();
    if (!text) return;
    setBusy(true);
    setError(null);
    try {
      await commentOnStation(stationId, { body: text, orgId });
      setBody("");
      onPosted();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [body, stationId, orgId, onPosted]);

  return (
    <div className="space-y-3">
      {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
      <label className="block">
        <span className="sr-only">Add a comment</span>
        <textarea
          rows={3}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Share what you found difficult, or a tip for this station."
          className={b2cInputBase}
        />
      </label>
      <div className="flex justify-end">
        <Button size="sm" onClick={submit} disabled={busy || body.trim().length === 0}>
          {busy ? "Posting…" : "Post comment"}
        </Button>
      </div>
    </div>
  );
}
