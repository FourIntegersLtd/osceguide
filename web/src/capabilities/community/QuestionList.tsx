"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { HiOutlineChevronRight } from "react-icons/hi2";
import { AsyncBoundary, Button, cn, productTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { askQuestion, listQuestions, type Post, type Room } from "@/capabilities/community/api";
import { SPECIALTY_TAGS_SORTED } from "@/capabilities/community/specialtyTags";
import { fieldClass, formatPostedDate, titleFromBody, useViewer, authorLabel, QuestionTags } from "@/capabilities/community/posts";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { b2cCard, b2cPanelDivided } from "@/foundation/ui/productTokens";

const {
  b2cFieldLabel,
  b2cPickerChipBase,
  b2cPickerChipSelected,
  b2cPickerChipUnselected,
} = productTokens;

/** One page of the feed. Questions are cursor-paginated; this is the first page. */
export const PAGE_SIZE = 100;

/**
 * Ask a question, and browse what everybody else asked.
 *
 * The list takes its audience from the workspace: a personal one asks for no
 * audience and gets the public pool plus every room the person is in; an
 * organisation's asks for that organisation and gets only its threads. The
 * composer posts into the same room, so a cohort's question is never published
 * to the world by accident.
 */
export function QuestionList({ room, roomName }: { room: Room; roomName: string | null }) {
  const [tag, setTag] = useState<string | null>(null);
  const { surface } = useSurface();
  const state = useAsync(
    (signal) => listQuestions({ room, limit: PAGE_SIZE, tag }, signal),
    [room.visibility, room.orgId, tag],
  );

  return (
    <div className="space-y-6">
      <B2CHero
        // The train arm's composer sits on the page itself, with no grey panel behind it.
        className={surface === "train" ? "!bg-transparent !p-0" : undefined}
        eyebrow="Ask a question"
        title={
          roomName
            ? `Need help? Ask below to get responses from ${roomName}.`
            : "Need help? Colleagues preparing for the same exam will answer."
        }
        action={
          <div className="w-full">
            <Composer room={room} onPosted={state.reload} />
          </div>
        }
      />

      <section className="space-y-3">
        <div>
          <h2 className="text-osce-subheading font-semibold text-osce-ink-900">Recent questions</h2>
          <p className="text-osce-meta text-b2c-text-muted">Browse what others are asking.</p>
        </div>

        <TagFilter selected={tag} onSelect={setTag} />

        <AsyncBoundary state={state}>
          {(page) =>
            page.items.length === 0 ? (
              <p className="rounded-osce-lg border border-dashed border-osce-border px-5 py-8 text-center text-osce-body text-b2c-text-muted">
                {tag
                  ? "No questions with that tag yet."
                  : roomName
                    ? `No questions in ${roomName} yet. Be the first to ask.`
                    : "No questions yet. Be the first to ask."}
              </p>
            ) : (
              <ul className={b2cPanelDivided}>
                {page.items.map((question) => (
                  <QuestionRow key={question.id} question={question} />
                ))}
              </ul>
            )
          }
        </AsyncBoundary>
      </section>
    </div>
  );
}

function TagFilter({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (tag: string | null) => void;
}) {
  return (
    <div className="touch-pan-x overflow-x-auto overflow-y-hidden overscroll-x-contain whitespace-nowrap pb-1">
      <div className="flex gap-2" role="group" aria-label="Filter questions by specialty">
        <FilterChip label="All" pressed={selected === null} onClick={() => onSelect(null)} />
        {SPECIALTY_TAGS_SORTED.map((specialty) => (
          <FilterChip
            key={specialty.key}
            label={specialty.name}
            pressed={selected === specialty.key}
            onClick={() => onSelect(selected === specialty.key ? null : specialty.key)}
          />
        ))}
      </div>
    </div>
  );
}

function FilterChip({
  label,
  pressed,
  onClick,
}: {
  label: string;
  pressed: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        b2cPickerChipBase,
        "shrink-0 rounded-md px-3 py-1.5",
        pressed ? b2cPickerChipSelected : b2cPickerChipUnselected,
      )}
    >
      {label}
    </button>
  );
}

function Composer({ room, onPosted }: { room: Room; onPosted: () => void }) {
  const [content, setContent] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The retiring client hid the tag row for the ortho app — its stations are
  // surgical, and the specialty list was GP medicine — and kept it for
  // everything else, so the gate is on the exam, not on the arm.
  const { code } = useCurrentExam();
  const showTags = code !== "ortho";

  const toggleTag = useCallback((key: string) => {
    setSelectedTags((current) =>
      current.includes(key) ? current.filter((tag) => tag !== key) : [...current, key],
    );
  }, []);

  const submit = useCallback(async () => {
    if (!content.trim()) {
      setError("Question content cannot be empty.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await askQuestion({
        title: titleFromBody(content),
        body: content,
        tags: selectedTags,
        room,
      });
      setContent("");
      setSelectedTags([]);
      onPosted();
    } catch (cause) {
      setError(errorMessage(cause) || "Could not post your question. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }, [content, selectedTags, room, onPosted]);

  return (
    <div className={cn(b2cCard, "space-y-4 p-5")}>
      <div>
        <label htmlFor="community-new-question" className={b2cFieldLabel}>New question</label>
        <textarea
          id="community-new-question"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Type your question here..."
          className={`${fieldClass} mt-1.5 min-h-[5.5rem] resize-y`}
          rows={3}
        />
      </div>
      {showTags ? (
        <div>
          <p className={b2cFieldLabel}>Tags</p>
          <div className="mt-1.5 touch-pan-x overflow-x-auto overflow-y-hidden overscroll-x-contain whitespace-nowrap pb-1">
            <div className="flex gap-2">
              {SPECIALTY_TAGS_SORTED.map((specialty) => (
                <FilterChip
                  key={specialty.key}
                  label={specialty.name}
                  pressed={selectedTags.includes(specialty.key)}
                  onClick={() => toggleTag(specialty.key)}
                />
              ))}
            </div>
          </div>
        </div>
      ) : null}
      {error ? <p className="text-osce-meta text-osce-danger-text">{error}</p> : null}
      <Button type="button" isLoading={isSubmitting} onClick={submit}>
        Post question
      </Button>
    </div>
  );
}

function QuestionRow({ question }: { question: Post }) {
  const { hrefFor } = useSurface();
  const viewer = useViewer();
  const replies = question.reply_count;

  return (
    <li>
      <Link
        href={hrefFor(`/discussion?question=${question.id}`)}
        className="group flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-b2c-surface-muted"
      >
        <span className="min-w-0 flex-1">
          <span className="block line-clamp-2 text-osce-body font-medium text-osce-ink-900">
            {question.title || titleFromBody(question.body)}
          </span>
          <span className="mt-0.5 block text-osce-meta text-b2c-text-muted">
            {authorLabel(question, viewer.id, viewer.name)} · {formatPostedDate(question.created_at)}
          </span>
        </span>
        <span className="hidden flex-wrap justify-end gap-1.5 sm:flex">
          <QuestionTags tags={question.tags} />
          <span className="inline-flex h-[22px] items-center rounded-[6px] bg-b2c-surface-muted px-2 text-osce-micro font-medium text-b2c-text-muted">
            {replies} {replies === 1 ? "reply" : "replies"}
          </span>
        </span>
        <HiOutlineChevronRight className="h-4 w-4 shrink-0 text-b2c-text-muted group-hover:text-osce-ink-900" aria-hidden />
      </Link>
    </li>
  );
}
