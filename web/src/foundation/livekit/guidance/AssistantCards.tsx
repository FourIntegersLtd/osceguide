"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useMaybeRoomContext } from "@livekit/components-react";
import type { CardRef, KnownAssistantCard } from "@/foundation/livekit/guidance/contracts";
import { useUiGuidance } from "@/foundation/livekit/guidance/useUiGuidance";

/**
 * What the tutor said it put on the screen.
 *
 * The voice session is not moved. A link is only there when the person asks
 * for it, and something they cannot open never arrives — the backend withholds
 * that card — so this draws the title and, where the ref leads somewhere, a way
 * to open it.
 *
 * Where a ref leads is the caller's to say through `linkFor`: this tier is
 * `foundation`, which may not import `capabilities` (ADR 0001), and knows no
 * route. A link is either a page (`href`) or something the caller opens in
 * place (`onOpen`), such as a help article inside the dock.
 */
export interface CardLink {
  /** What kind of thing this is, shown above the title ("Station", "Slides"). */
  eyebrow: string;
  /** The words on the link. */
  label: string;
  href?: string;
  onOpen?: () => void;
}

export type CardLinkFor = (ref: CardRef) => CardLink | null;

/** Listens on the open voice room. Mount inside `VoiceRoom`. */
export function AssistantCardSlot({ linkFor }: { linkFor: CardLinkFor }) {
  const room = useMaybeRoomContext();
  const { cards, dismissCard } = useUiGuidance(room);
  return <AssistantCards cards={cards} onDismiss={dismissCard} linkFor={linkFor} />;
}

export function AssistantCards({
  cards,
  onDismiss,
  linkFor,
}: {
  cards: readonly KnownAssistantCard[];
  onDismiss: (kind: KnownAssistantCard["card"]) => void;
  linkFor: CardLinkFor;
}) {
  if (cards.length === 0) return null;

  return (
    <div className="mb-3 flex flex-col gap-2">
      {cards.map((card) =>
        card.card === "suggestion" ? (
          <SuggestionCard
            key="suggestion"
            card={card}
            link={card.ref ? linkFor(card.ref) : null}
            onDismiss={() => onDismiss("suggestion")}
          />
        ) : (
          <CitationsCard
            key="citations"
            card={card}
            linkFor={linkFor}
            onDismiss={() => onDismiss("citations")}
          />
        ),
      )}
    </div>
  );
}

function SuggestionCard({
  card,
  link,
  onDismiss,
}: {
  card: Extract<KnownAssistantCard, { card: "suggestion" }>;
  link: CardLink | null;
  onDismiss: () => void;
}) {
  return (
    <article className="rounded-lg border border-osce-accent-subtle bg-osce-accent-muted px-3 py-3">
      <header className="flex items-start justify-between gap-3">
        <p className="text-osce-meta font-medium text-osce-accent">{link?.eyebrow ?? "Suggested"}</p>
        <Dismiss onClick={onDismiss} />
      </header>
      <p className="mt-1 text-osce-body font-semibold text-osce-ink-900">{card.title}</p>
      {card.reason ? (
        <p className="mt-1 text-osce-meta leading-relaxed text-osce-ink-600">{card.reason}</p>
      ) : null}
      {link ? (
        <OpenLink link={link} className="mt-2 inline-block text-osce-meta font-medium text-osce-accent hover:underline">
          {link.label}
        </OpenLink>
      ) : null}
    </article>
  );
}

function CitationsCard({
  card,
  linkFor,
  onDismiss,
}: {
  card: Extract<KnownAssistantCard, { card: "citations" }>;
  linkFor: CardLinkFor;
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
          const link = citation.ref ? linkFor(citation.ref) : null;
          const title = <span className="text-osce-body text-osce-ink-900">{citation.title}</span>;
          return (
            <li key={`${citation.title}-${index}`}>
              {link ? (
                <OpenLink link={link} className="text-left hover:underline">
                  {title}
                </OpenLink>
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

/** A page link when the ref has a page, otherwise a button that opens it in place. */
function OpenLink({
  link,
  className,
  children,
}: {
  link: CardLink;
  className: string;
  children: ReactNode;
}) {
  if (link.href) {
    return (
      <Link href={link.href} className={className}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" onClick={link.onOpen} className={className}>
      {children}
    </button>
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
