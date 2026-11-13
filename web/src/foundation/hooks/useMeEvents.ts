"use client";

import { useEffect, useRef } from "react";
import { mintStreamTicket, platformApiUrl } from "@/foundation/platform-client";
import { streamUrl } from "./eventStreamProtocol";

/** Every named event `/me/events` can carry. Kept in sync with the backend's `MeEventEnvelope`. */
const ME_EVENT_NAMES = [
  "attempt",
  "practice.session_updated",
  "practice.matched",
  "practice.accepted",
  "cv.read",
  "media.updated",
  "station_import.updated",
  "station.updated",
  "coverage",
  "nonverbal",
  "message.received",
  "community_reply",
  "debrief",
] as const;
export type MeEventName = (typeof ME_EVENT_NAMES)[number];

/** A synthetic event this hook invents, never sent by the server: "go re-read your own state". */
export type MeSignal = MeEventName | "resync";

export interface MeEvent {
  name: MeSignal;
  /** The small object of ids the server sent, or `{}` for a synthetic `resync`. */
  data: Readonly<Record<string, string>>;
}

type Listener = (event: MeEvent) => void;

/** Names the raw stream carries that are plumbing, not something a caller ever wants. */
const CONTROL_FRAMES = new Set(["connected", "ping"]);

/**
 * The single `/me/events` connection for this tab, shared by every `useMeEvents` caller.
 *
 * One person can have a dozen live-updating panels open in one tab (a session screen, a
 * coverage feed, a CV card); each used to poll on its own timer. This opens one `EventSource`
 * no matter how many components ask, reference-counted so the last one to unmount closes it.
 */
class MeEventHub {
  private source: EventSource | null = null;
  private connecting = false;
  private listeners = new Set<Listener>();
  private retryAttempt = 0;
  private retryTimer: number | undefined;

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    this.ensureConnected();
    return () => {
      this.listeners.delete(listener);
      if (this.listeners.size === 0) this.teardown();
    };
  }

  /** Every open panel re-reads its own state: used on `visibilitychange` back to visible. */
  broadcastResync(): void {
    this.emit({ name: "resync", data: {} });
  }

  private emit(event: MeEvent): void {
    for (const listener of this.listeners) listener(event);
  }

  private ensureConnected(): void {
    if (this.source || this.connecting) return;
    this.connecting = true;
    void this.connect().finally(() => {
      this.connecting = false;
    });
  }

  private async connect(): Promise<void> {
    // `EventSource` cannot send headers, so a fresh single-use ticket buys this connection in.
    const ticket = await mintStreamTicket();
    if (this.listeners.size === 0) return; // everybody left while the ticket was minting
    const source = new EventSource(
      streamUrl(platformApiUrl(), "/api/v1/me/events", window.location.origin, ticket),
    );
    this.source = source;

    source.onopen = () => {
      this.retryAttempt = 0;
    };

    const forward = (raw: string) => {
      if (CONTROL_FRAMES.has(raw)) {
        if (raw === "connected") this.broadcastResync();
        return;
      }
      source.addEventListener(raw, (event) => {
        let data: Record<string, string> = {};
        if (event instanceof MessageEvent && event.data) {
          try {
            data = JSON.parse(event.data) as Record<string, string>;
          } catch {
            data = {};
          }
        }
        this.emit({ name: raw as MeEventName, data });
      });
    };
    [...ME_EVENT_NAMES, "connected", "ping"].forEach(forward);

    source.onerror = () => {
      source.close();
      if (this.source === source) this.source = null;
      if (this.listeners.size === 0) return;
      // A thundering-herd reconnect after a blip is exactly what killed the polling
      // this hook replaces; back off to a ceiling instead of retrying in lockstep.
      const delay = Math.min(30_000, 1_000 * 2 ** this.retryAttempt);
      this.retryAttempt += 1;
      this.retryTimer = window.setTimeout(() => this.ensureConnected(), delay);
    };
  }

  private teardown(): void {
    this.source?.close();
    this.source = null;
    if (this.retryTimer) window.clearTimeout(this.retryTimer);
  }
}

let hub: MeEventHub | null = null;
function sharedHub(): MeEventHub {
  hub ??= new MeEventHub();
  return hub;
}

/**
 * Subscribe to this user's own event stream, replacing a `setInterval` poll.
 *
 * `filter` names the events this caller cares about; a `resync` is always delivered
 * regardless of `filter`, since it means "the connection just came back" or "the tab just
 * became visible again" — either way, whatever this caller was polling for might have moved
 * on without a name event to say so, so it re-reads on general principle.
 *
 * Every caller in a tab shares one `EventSource` (see `MeEventHub`); this hook only tracks
 * this component's own listener and its own `filter`.
 */
export function useMeEvents(filter: readonly MeEventName[] | null, onEvent: (event: MeEvent) => void): void {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;
  const filterKey = filter ? filter.join(",") : "";

  useEffect(() => {
    const wanted = filterKey ? new Set(filterKey.split(",")) : null;
    const listener: Listener = (event) => {
      if (event.name !== "resync" && wanted && !wanted.has(event.name)) return;
      handlerRef.current(event);
    };
    const unsubscribe = sharedHub().subscribe(listener);

    const onVisible = () => {
      if (document.visibilityState === "visible") sharedHub().broadcastResync();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      unsubscribe();
      document.removeEventListener("visibilitychange", onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- filterKey is the stable form of filter
  }, [filterKey]);
}
