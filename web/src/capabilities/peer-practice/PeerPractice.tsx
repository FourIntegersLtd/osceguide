"use client";

import { useCallback, useEffect, useState } from "react";
import { LuClock, LuUsers } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card, Input, PageHeader, Spinner } from "@/foundation/ui";
import { errorMessage, useAsync, useEventStream } from "@/foundation/hooks";
import { AgentTile, VoiceRoom, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { listExams } from "@/capabilities/stations";
import {
  claimSlot,
  joinPeerSession,
  joinQueue,
  leaveQueue,
  listSlots,
  offerSlot,
  withdrawSlot,
  type QueueStatus,
} from "@/capabilities/peer-practice/api";

/**
 * Practise with another person.
 *
 * `orgId` scopes both halves to one organisation's cohort when a surface
 * supplies it. The component itself knows only that an audience exists.
 */
export function PeerPractice({ orgId = null }: { orgId?: string | null }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Practise with someone"
        description="Queue to be paired now, or arrange a time with a peer."
      />
      <Queue orgId={orgId} />
      <Marketplace orgId={orgId} />
    </div>
  );
}

function Queue({ orgId }: { orgId: string | null }) {
  const exams = useAsync((signal) => listExams(signal), []);
  const [examCode, setExamCode] = useState<string>("");
  const [entry, setEntry] = useState<QueueStatus | null>(null);
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const mic = useMicPreflight(entry !== null);

  // The queue pushes its own state, so there is no poll and no guessing when a
  // partner appears.
  const stream = useEventStream<QueueStatus>(
    entry ? `/api/v1/peer-practice/queue/${entry.entry_id}/stream` : null,
  );
  const status = stream.data ?? entry;

  useEffect(() => {
    if (!status?.session_id || grant) return;
    // Matched. Get into the room without asking again — both people are waiting.
    void (async () => {
      try {
        if (mic.status !== "ready") await mic.request();
        setGrant(await joinPeerSession(status.session_id!));
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      }
    })();
  }, [status?.session_id, grant, mic]);

  const join = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      if (mic.status !== "ready") await mic.request();
      setEntry(await joinQueue(examCode || exams.data?.items[0]?.code || "sca", orgId));
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [examCode, exams.data, orgId, mic]);

  const leave = useCallback(async () => {
    if (!entry) return;
    setBusy(true);
    try {
      await leaveQueue(entry.entry_id);
      setEntry(null);
      setGrant(null);
    } finally {
      setBusy(false);
    }
  }, [entry]);

  if (grant) {
    return (
      <Card title="You are paired">
        <VoiceRoom
          grant={grant}
          onDisconnected={() => {
            setGrant(null);
            setEntry(null);
          }}
        >
          <div className="flex flex-col items-center gap-4">
            <AgentTile name="Your partner" detail="One of you is the doctor" className="w-full max-w-sm" />
            <Button variant="danger" onClick={() => setGrant(null)}>
              Leave
            </Button>
          </div>
        </VoiceRoom>
      </Card>
    );
  }

  return (
    <Card title="Queue now" description="You will be paired with whoever else is waiting.">
      <div className="flex flex-col gap-3">
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        {mic.message && <Alert tone="warning">{mic.message}</Alert>}

        {status ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-sm text-ink-muted">
              <Spinner />
              {status.position !== null && status.position !== undefined
                ? `You are number ${status.position} in the queue`
                : "Waiting for a partner"}
              <Badge tone="neutral">
                <LuUsers className="mr-1 h-3 w-3" aria-hidden /> {status.waiting_count} waiting
              </Badge>
            </span>
            <Button variant="secondary" onClick={leave} disabled={busy}>
              Leave the queue
            </Button>
          </div>
        ) : (
          <AsyncBoundary state={exams}>
            {(page) => (
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium text-ink">Exam</span>
                  <select
                    value={examCode || page.items[0]?.code || ""}
                    onChange={(event) => setExamCode(event.target.value)}
                    className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
                  >
                    {page.items.map((exam) => (
                      <option key={exam.id} value={exam.code}>
                        {exam.name}
                      </option>
                    ))}
                  </select>
                </label>
                <Button onClick={join} disabled={busy}>
                  {busy ? <Spinner /> : "Join the queue"}
                </Button>
              </div>
            )}
          </AsyncBoundary>
        )}
      </div>
    </Card>
  );
}

function Marketplace({ orgId }: { orgId: string | null }) {
  const state = useAsync((signal) => listSlots({}, signal), []);
  const exams = useAsync((signal) => listExams(signal), []);
  const [offering, setOffering] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const act = useCallback(
    async (id: string, action: () => Promise<unknown>) => {
      setBusy(id);
      try {
        await action();
        state.reload();
      } finally {
        setBusy(null);
      }
    },
    [state],
  );

  return (
    <Card
      title="Arrange a time"
      description="Offer a slot, or claim one somebody else has offered."
      actions={
        <Button variant="secondary" size="sm" onClick={() => setOffering((open) => !open)}>
          {offering ? "Cancel" : "Offer a slot"}
        </Button>
      }
    >
      <div className="flex flex-col gap-4">
        {offering && (
          <AsyncBoundary state={exams}>
            {(page) => (
              <OfferForm
                examCodes={page.items.map((exam) => ({ code: exam.code, name: exam.name }))}
                orgId={orgId}
                onOffered={() => {
                  setOffering(false);
                  state.reload();
                }}
              />
            )}
          </AsyncBoundary>
        )}

        <AsyncBoundary
          state={state}
          isEmpty={(page) => page.items.length === 0}
          empty={{ title: "No slots offered", description: "Offer one and somebody may claim it." }}
        >
          {(page) => (
            <ul className="divide-y divide-border">
              {page.items.map((slot) => (
                <li key={slot.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 text-sm font-medium text-ink">
                      <LuClock className="h-3.5 w-3.5 text-ink-subtle" aria-hidden />
                      {new Date(slot.starts_at).toLocaleString()}
                    </p>
                    <p className="text-xs text-ink-subtle">
                      {slot.exam_code.toUpperCase()} · {slot.duration_minutes} minutes
                      {slot.note ? ` · ${slot.note}` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={slot.status === "available" ? "success" : "neutral"}>
                      {slot.status}
                    </Badge>
                    {slot.is_mine ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={busy !== null || slot.status !== "available"}
                        onClick={() => act(slot.id, () => withdrawSlot(slot.id))}
                      >
                        Withdraw
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        disabled={busy !== null || slot.status !== "available"}
                        onClick={() => act(slot.id, () => claimSlot(slot.id))}
                      >
                        {busy === slot.id ? <Spinner /> : "Claim"}
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </AsyncBoundary>
      </div>
    </Card>
  );
}

function OfferForm({
  examCodes,
  orgId,
  onOffered,
}: {
  examCodes: { code: string; name: string }[];
  orgId: string | null;
  onOffered: () => void;
}) {
  const [examCode, setExamCode] = useState(examCodes[0]?.code ?? "");
  const [startsAt, setStartsAt] = useState("");
  const [duration, setDuration] = useState(30);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [note, setNote] = useState("");

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await offerSlot({
          examCode,
          startsAt: new Date(startsAt).toISOString(),
          durationMinutes: duration,
          note: note.trim() || null,
          orgId,
        });
        onOffered();
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [examCode, startsAt, duration, note, orgId, onOffered],
  );

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 rounded-panel border border-border p-4">
      {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink">Exam</span>
          <select
            value={examCode}
            onChange={(event) => setExamCode(event.target.value)}
            className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
          >
            {examCodes.map((exam) => (
              <option key={exam.code} value={exam.code}>
                {exam.name}
              </option>
            ))}
          </select>
        </label>
        <Input
          label="Starts at"
          type="datetime-local"
          required
          value={startsAt}
          onChange={(event) => setStartsAt(event.target.value)}
        />
        <Input
          label="Minutes"
          type="number"
          min={10}
          value={duration}
          onChange={(event) => setDuration(Number(event.target.value))}
        />
      </div>
      <Input
        label="Note"
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder="Anything your partner should know"
      />
      <div className="flex justify-end">
        <Button type="submit" disabled={busy || !startsAt}>
          Offer slot
        </Button>
      </div>
    </form>
  );
}
