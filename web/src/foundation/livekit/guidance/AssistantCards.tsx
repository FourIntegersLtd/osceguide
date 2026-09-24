"use client";

import Link from "next/link";
import { useMaybeRoomContext } from "@livekit/components-react";
import type { KnownAssistantCard } from "@/foundation/livekit/guidance/contracts";
import { useUiGuidance } from "@/foundation/livekit/guidance/useUiGuidance";

/**
 * What the tutor said it put on the screen.
 *
 * The voice session is not moved. A link is only there when the person asks
 * for it, and a station they cannot open never arrives — the backend withholds
 * that card — so this draws the title and, for a source with a slug, the page.
 *
 * `hrefFor` arrives as a prop rather than from `useSurface()`: this tier is
 * `foundation`, which may not import `capabilities` (ADR 0001), so a caller
 * that already has the surface context hands over just the one function it
 * needs.
 */
type HrefFor = (path: string) => string;

/** Listens on the open voice room. Mount inside `VoiceRoom`. */
export function AssistantCardSlot({ hrefFor }: { hrefFor: HrefFor }) {
  const room = useMaybeRoomContext();
  const { cards, dismissCard } = useUiGuidance(room);
  return <AssistantCards cards={cards} onDismiss={dismissCard} hrefFor={hrefFor} />;
}

export function AssistantCards({
  cards,
  onDismiss,
  hrefFor,
}: {
  cards: readonly KnownAssistantCard[];
  onDismiss: (kind: KnownAssistantCard["card"]) => void;
  hrefFor: HrefFor;
}) {
  if (cards.length === 0) return null;

  return (
    <div className="mb-3 flex flex-col gap-2">
      {cards.map((card) =>
        card.card === "suggestion" ? (
          <SuggestionCard
            key="suggestion"
            card={card}
            href={hrefFor("/stations")}
            onDismiss={() => onDismiss("suggestion")}
          />
        ) : (
          <CitationsCard
            key="citations"
            card={card}
            hrefFor={hrefFor}
            onDismiss={() => onDismiss("citations")}
          />
        ),
      )}
    </div>
  );
}

function SuggestionCard({
  card,
  href,
  onDismiss,
}: {
  card: Extract<KnownAssistantCard, { card: "suggestion" }>;
  href: string;
  onDismiss: () => void;
}) {
  return (
    <article className="rounded-lg border border-osce-accent-subtle bg-osce-accent-muted px-3 py-3">
      <header className="flex items-start justify-between gap-3">
        <p className="text-osce-meta font-medium text-osce-accent">Station</p>
        <Dismiss onClick={onDismiss} />
      </header>
      <p className="mt-1 text-osce-body font-semibold text-osce-ink-900">{card.title}</p>
      {card.reason ? (
        <p className="mt-1 text-osce-meta leading-relaxed text-osce-ink-600">{card.reason}</p>
      ) : null}
      <Link href={href} className="mt-2 inline-block text-osce-meta font-medium text-osce-accent hover:underline">
        Open the station library
      </Link>
    </article>
  );
}

function CitationsCard({
  card,
  hrefFor,
  onDismiss,
}: {
  card: Extract<KnownAssistantCard, { card: "citations" }>;
  hrefFor: (path: string) => string;
  onDismiss: () => void;
}) {
  return (
    <article className="rounded-lg border border-osce-border bg-white px-3 py-3">
      <header className="flex items-start justify-between gap-3">
        <p className="text-osce-meta font-medium text-osce-ink-600">Sources</p>
        <Dismiss onClick={onDismiss} />
      </header>
      <ul className="mt-2 flex flex-col gap-2">
        {card.citations.map((citation, index) => {
          const slug = citation.ref?.slug?.trim();
          const title = <span className="text-osce-body text-osce-ink-900">{citation.title}</span>;
          return (
            <li key={`${citation.title}-${index}`}>
              {slug ? (
                <Link href={hrefFor(`/library/${encodeURIComponent(slug)}`)} className="hover:underline">
                  {title}
                </Link>
              ) : (
                title
              )}
              {citation.section ? (
                <p className="text-osce-meta text-osce-ink-500">{citation.section}</p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </article>
  );
}

function Dismiss({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-osce-meta text-osce-ink-500 hover:text-osce-ink-800"
    >
      Dismiss
    </button>
  );
}
