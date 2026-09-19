"use client";

import Link from "next/link";
import { useState } from "react";
import Markdown from "react-markdown";
import { LuArrowLeft, LuChevronLeft, LuChevronRight } from "react-icons/lu";
import { AsyncBoundary, Badge, Button, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  audioUrl,
  bodyMarkdown,
  deckSlides,
  readMedia,
  type MediaItem,
} from "@/capabilities/media/api";

export function MediaItemView({ slug }: { slug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readMedia(slug, signal), [slug]);

  return (
    <div className="flex flex-col gap-6">
      <Link
        href={hrefFor("/library")}
        className="inline-flex w-fit items-center gap-1.5 text-sm text-ink-muted hover:text-ink"
      >
        <LuArrowLeft className="h-4 w-4" aria-hidden /> Study material
      </Link>

      <AsyncBoundary state={state}>
        {(item) => (
          <>
            <PageHeader
              title={item.title}
              description={item.summary}
              actions={item.exam_code ? <Badge tone="accent">{item.exam_code.toUpperCase()}</Badge> : null}
            />
            <MediaBody item={item} />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

/** One switch on `kind`, so adding a fifth kind is one case rather than a new screen. */
function MediaBody({ item }: { item: MediaItem }) {
  if (item.kind === "slide_deck") return <Deck item={item} />;
  if (item.kind === "podcast") return <Episode item={item} />;
  return <Prose item={item} />;
}

function Prose({ item }: { item: MediaItem }) {
  const markdown = bodyMarkdown(item);
  if (!markdown) {
    return <Card>This item has no content yet.</Card>;
  }
  return (
    <article className="prose-platform max-w-3xl text-sm leading-6 text-ink">
      <Markdown>{markdown}</Markdown>
    </article>
  );
}

function Episode({ item }: { item: MediaItem }) {
  const url = audioUrl(item);
  return (
    <div className="flex max-w-3xl flex-col gap-5">
      {url ? (
        <audio controls src={url} className="w-full" preload="none" />
      ) : (
        <Card>This episode has no audio attached yet.</Card>
      )}
      <Prose item={item} />
    </div>
  );
}

function Deck({ item }: { item: MediaItem }) {
  const slides = deckSlides(item);
  const [index, setIndex] = useState(0);

  if (slides.length === 0) return <Card>This deck has no slides yet.</Card>;

  // Clamped rather than trusted: a deck edited between the list and the read
  // would otherwise index past the end and render a blank panel.
  const safeIndex = Math.min(index, slides.length - 1);
  const slide = slides[safeIndex];

  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <Card className="min-h-[18rem]">
        {slide?.image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={slide.image_url} alt="" className="mb-4 w-full rounded-control" />
        )}
        {slide?.title && <h2 className="mb-2 text-lg font-semibold text-ink">{slide.title}</h2>}
        {slide?.body && (
          <div className="text-sm leading-6 text-ink-muted">
            <Markdown>{slide.body}</Markdown>
          </div>
        )}
      </Card>

      <div className="flex items-center justify-between gap-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={safeIndex === 0}
        >
          <LuChevronLeft className="h-4 w-4" aria-hidden /> Previous
        </Button>
        <p aria-live="polite" className="text-sm text-ink-muted">
          Slide {safeIndex + 1} of {slides.length}
        </p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setIndex((i) => Math.min(slides.length - 1, i + 1))}
          disabled={safeIndex === slides.length - 1}
        >
          Next <LuChevronRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
