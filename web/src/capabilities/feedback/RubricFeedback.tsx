"use client";

import { useMemo } from "react";
import type { IconType } from "react-icons";
import {
  HiOutlineArrowTrendingUp,
  HiOutlineCheckCircle,
  HiOutlineChatBubbleLeftEllipsis,
  HiOutlineExclamationTriangle,
  HiOutlineLightBulb,
  HiOutlineListBullet,
  HiOutlineSparkles,
  HiOutlineXCircle,
} from "react-icons/hi2";
import { Dropdown } from "@/foundation/table";
import { Badge, B2CEmptyState, B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader, cn, productTokens } from "@/foundation/ui";
import { GradeCircle } from "@/capabilities/feedback/GradeCircle";
import { toneVariant, type MarkedResult, type MarkingRubric } from "@/capabilities/feedback/rubric";
import {
  feedbackModel,
  type AnswerView,
  type CompetencyView,
  type DomainView,
  type FieldRole,
  type RatingView,
  type SectionView,
} from "@/capabilities/feedback/rubricView";
import { HiOutlineFaceFrown, HiOutlineInformationCircle } from "react-icons/hi2";

const { b2cMonoEyebrow } = productTokens;

/**
 * One marked result, rendered from its rubric.
 *
 * Every exam goes through this one component. What it draws is decided by the
 * rubric: its sections in order, each answer by its field's type and role, each
 * rating by the rating's kind, and the totals the backend computed. There is
 * no exam code anywhere in it; a new rubric renders without a change here.
 *
 * The same component shows a consumer their practice feedback and an examiner
 * or admin the machine's view of a candidate's; nothing here asks who is
 * looking.
 *
 * `narrow` is for a half-width column (an examiner's review page puts it
 * beside the form): domain cards then stack one per row instead of being
 * squeezed into a three-column grid sized for the whole page.
 */
export function RubricFeedback({
  rubric,
  result,
  narrow = false,
}: {
  rubric: MarkingRubric;
  result: MarkedResult;
  narrow?: boolean;
}) {
  const model = useMemo(() => feedbackModel(rubric, result), [rubric, result]);

  if (model.blocks.length === 0) {
    return (
      <B2CEmptyState
        icon={HiOutlineFaceFrown}
        title="No feedback recorded"
        description="This marking has no answers the rubric recognises."
      />
    );
  }

  const domains = model.blocks.filter((block): block is DomainView => block.kind === "domain");
  const sections = model.blocks.filter((block): block is SectionView => block.kind === "section");
  // A selector (Ortho's station type) says which alternative was marked, so
  // it belongs with the headline rather than after every domain.
  const selectors = sections.filter((section) => section.answers.every((answer) => answer.role === "selector"));
  const narrative = sections.filter((section) => !selectors.includes(section));
  // A list that sits at the top of the result on its own (a v1 rubric's
  // actionable feedback and clinical analysis) is one card, not a section:
  // those share a single dropdown, side by side, instead of one dropdown each.
  const loneLists = narrative.filter((section) => section.answers.length === 1 && section.answers[0]?.type === "list");
  const fullSections = narrative.filter((section) => !loneLists.includes(section));

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 rounded-osce-2xl bg-b2c-surface-muted p-6 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <p className={b2cMonoEyebrow}>Your mark</p>
          {model.header.total ? (
            <p className="mt-1.5 text-osce-title font-semibold text-osce-ink-900">
              <span className="font-mono tabular-nums">{model.header.total}</span>{" "}
              <span className="font-normal text-b2c-text-muted">{model.header.caption}</span>
            </p>
          ) : null}
          {model.header.passLine ? (
            <p className="mt-1 text-osce-meta text-b2c-text-muted">{model.header.passLine}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2 md:justify-end">
          {model.header.outcome ? (
            <Badge variant={model.header.passed ? "success" : "danger"}>{model.header.outcome}</Badge>
          ) : null}
          {model.header.band ? (
            <Badge variant={toneVariant(model.header.band.tone)}>{model.header.band.name}</Badge>
          ) : null}
          {selectors.flatMap((section) =>
            section.answers.map((answer) =>
              answer.type === "tag" || answer.type === "text" ? (
                <Badge key={section.id} variant="accent">
                  {answer.label}: {answer.text}
                </Badge>
              ) : null,
            ),
          )}
        </div>
      </div>

      {domains.length > 0 ? (
        <section className="space-y-3">
          <h2 className={b2cMonoEyebrow}>By domain</h2>
          <div className={cn("grid grid-cols-1 gap-4", !narrow && domains.length > 1 && "md:grid-cols-2 xl:grid-cols-3")}>
            {domains.map((domain) => (
              <DomainCard key={domain.id} domain={domain} />
            ))}
          </div>
        </section>
      ) : null}

      {loneLists.length > 0 ? (
        <Dropdown
          defaultOpen
          title={loneLists.map((section) => section.title).join(" and ")}
          icon={<HiOutlineListBullet aria-hidden />}
        >
          <SectionAnswers answers={loneLists.flatMap((section) => section.answers)} />
        </Dropdown>
      ) : null}

      {fullSections.map((section) => (
        <Dropdown key={section.id} defaultOpen title={section.title} icon={<HiOutlineListBullet aria-hidden />}>
          <SectionAnswers answers={section.answers} />
        </Dropdown>
      ))}

      <p className="flex items-start gap-2 text-osce-meta text-b2c-text-muted">
        <HiOutlineInformationCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        This consultation analysis is for formative training only and cannot be used as an
        indication of performance in the exam.
      </p>
    </section>
  );
}

function DomainCard({ domain }: { domain: DomainView }) {
  return (
    <section className="flex flex-col rounded-osce-lg border border-osce-border bg-osce-surface">
      <header className="flex items-start gap-3 px-5 pb-1 pt-[18px]">
        <h3 className="min-w-0 flex-1 text-osce-subheading font-semibold text-osce-ink-900">{domain.title}</h3>
        {domain.aggregate ? (
          <span className="shrink-0 font-mono text-osce-body font-medium tabular-nums text-osce-ink-900">
            {domain.aggregate}
          </span>
        ) : null}
      </header>
      <div className="flex flex-1 flex-col px-5 pb-5 pt-3">
        {domain.passLine || domain.passed !== null ? (
          <div className="mb-2 flex items-center gap-2">
            {domain.passed !== null ? (
              <Badge size="xs" variant={domain.passed ? "success" : "danger"}>
                {domain.passed ? "Met the pass line" : "Below the pass line"}
              </Badge>
            ) : null}
            {domain.passLine ? <span className="text-osce-meta text-b2c-text-muted">{domain.passLine}</span> : null}
          </div>
        ) : null}
        <div className="divide-y divide-osce-border-light">
          {domain.competencies.map((competency) => (
            <CompetencyRow key={competency.id} competency={competency} />
          ))}
        </div>
        {domain.answers.length > 0 ? (
          <div className="mt-4 space-y-4 border-t border-b2c-border pt-4">
            <Answers answers={domain.answers} />
          </div>
        ) : null}
        <GradeCounts competencies={domain.competencies} />
      </div>
    </section>
  );
}

/**
 * The foot of a domain card: how many competencies got each grade, as the
 * legacy domain cards showed. Only scale grades are counted; a domain marked
 * with numbers or ticks has no foot.
 */
function GradeCounts({ competencies }: { competencies: CompetencyView[] }) {
  const countByGrade = new Map<string, { tone: string | null; count: number }>();
  for (const competency of competencies) {
    if (competency.rating?.shape !== "grade") continue;
    const tally = countByGrade.get(competency.rating.text) ?? { tone: competency.rating.tone, count: 0 };
    countByGrade.set(competency.rating.text, { ...tally, count: tally.count + 1 });
  }
  if (countByGrade.size === 0) return null;
  return (
    <div className="mt-auto flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-b2c-border pt-4">
      {[...countByGrade].map(([grade, tally]) => (
        <span key={grade} className="inline-flex items-center text-osce-body text-b2c-text-secondary">
          <GradeCircle grade={grade} tone={tally.tone} />
          <span className="font-semibold text-osce-ink-900">{tally.count}</span>
        </span>
      ))}
    </div>
  );
}

function CompetencyRow({ competency }: { competency: CompetencyView }) {
  return (
    <div className="space-y-2 py-4 first:pt-1">
      <div className="flex items-start gap-1">
        {competency.rating ? <RatingMark rating={competency.rating} /> : null}
        <span className="pt-0.5 font-medium text-osce-ink-900">{competency.label}</span>
      </div>
      {competency.answers.length > 0 ? (
        <div className="space-y-2 sm:pl-9">
          <Answers answers={competency.answers} />
        </div>
      ) : null}
      {competency.hint ? (
        <details className="sm:pl-9">
          <summary className="cursor-pointer text-osce-meta font-medium text-osce-accent">What good looks like</summary>
          <p className="mt-1 text-osce-meta leading-relaxed text-b2c-text-secondary">{competency.hint}</p>
        </details>
      ) : null}
    </div>
  );
}

/** A rating by kind: a disc for a scale grade, a chip for a number, a tick or cross for met. */
function RatingMark({ rating }: { rating: RatingView }) {
  if (rating.shape === "grade") return <GradeCircle grade={rating.text} tone={rating.tone} />;
  if (rating.shape === "check") {
    const Icon = rating.met ? HiOutlineCheckCircle : HiOutlineXCircle;
    return (
      <span
        className={cn(
          "mr-2 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          rating.met ? "bg-osce-success-bg text-osce-success-text" : "bg-osce-danger-bg text-osce-danger",
        )}
        title={rating.text}
      >
        <Icon className="h-5 w-5" aria-label={rating.text} />
      </span>
    );
  }
  return (
    <Badge className="mr-2 shrink-0" variant={toneVariant(rating.tone)}>
      {rating.text}
    </Badge>
  );
}

/** How each role reads: the icon beside a list and its colour. */
const ROLE_ICON: Partial<Record<FieldRole, { icon: IconType; className: string }>> = {
  strength: { icon: HiOutlineSparkles, className: "text-osce-success-text" },
  improvement: { icon: HiOutlineArrowTrendingUp, className: "text-osce-warning-text" },
  action: { icon: HiOutlineLightBulb, className: "text-osce-accent" },
  flag: { icon: HiOutlineExclamationTriangle, className: "text-osce-danger" },
  evidence: { icon: HiOutlineChatBubbleLeftEllipsis, className: "text-b2c-text-muted" },
};

/** How a section-level list reads as a legacy clinical-analysis card: dot, tint and bullet by role. */
const ROLE_CARD: Partial<Record<FieldRole, { dot: string; body: string; bullet: string }>> = {
  strength: { dot: "bg-osce-success-icon", body: "bg-osce-success-bg", bullet: "•" },
  improvement: { dot: "bg-osce-warning-text", body: "bg-osce-warning-bg", bullet: "→" },
  action: { dot: "bg-osce-accent", body: "bg-osce-accent-muted", bullet: "→" },
  flag: { dot: "bg-osce-danger", body: "bg-osce-danger-bg", bullet: "!" },
};
const PLAIN_ROLE_CARD = { dot: "bg-b2c-text-muted", body: "bg-osce-accent-muted", bullet: "•" };

/** The three columns of a legacy category card, in their order, by the role of the list they hold. */
const CATEGORY_COLUMNS: Array<{ role: FieldRole; border: string; title: string; bullet: string }> = [
  { role: "strength", border: "border-osce-success-icon", title: "text-osce-success-text", bullet: "" },
  { role: "improvement", border: "border-osce-danger", title: "text-osce-danger-hover", bullet: "" },
  { role: "action", border: "border-osce-accent-light", title: "text-osce-accent-hover", bullet: "→ " },
];

type ListAnswer = Extract<AnswerView, { type: "list" }>;
type GroupAnswer = Extract<AnswerView, { type: "group" }>;

/** A group is a category when it holds a strengths, improvements or actions list. */
function isCategory(answer: AnswerView): answer is GroupAnswer {
  return (
    answer.type === "group" &&
    answer.answers.some(
      (child) => child.type === "list" && CATEGORY_COLUMNS.some((column) => column.role === child.role),
    )
  );
}

/**
 * A narrative section's answers, laid out as the legacy feedback screen: each
 * list a tinted card in a two-column grid (clinical analysis), each category
 * group a card of strengths / improvements / actions columns, and anything
 * else by its own type. Decided by field type and role, never by exam.
 */
function SectionAnswers({ answers }: { answers: AnswerView[] }) {
  const lists = answers.filter((answer): answer is ListAnswer => answer.type === "list");
  const categories = answers.filter(isCategory);
  const others = answers.filter((answer) => answer.type !== "list" && !isCategory(answer));
  return (
    <div className="space-y-4">
      {others.length > 0 ? <Answers answers={others} /> : null}
      {lists.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {lists.map((list) => (
            <ListCard key={list.label} answer={list} />
          ))}
        </div>
      ) : null}
      {categories.map((category) => (
        <CategoryCard key={category.label} answer={category} />
      ))}
    </div>
  );
}

function ListCard({ answer }: { answer: ListAnswer }) {
  const look = ROLE_CARD[answer.role] ?? PLAIN_ROLE_CARD;
  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>
        <span className={cn("h-2 w-2 shrink-0 rounded-full", look.dot)} aria-hidden />
        {answer.label}
      </B2CPanelCardHeader>
      <B2CPanelCardBody className={look.body}>
        <ul className="space-y-2">
          {answer.items.map((item, index) => (
            <li key={index} className="flex gap-2 text-osce-body leading-relaxed text-b2c-text-secondary">
              <span className="shrink-0 font-semibold" aria-hidden>
                {look.bullet}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function CategoryCard({ answer }: { answer: GroupAnswer }) {
  const columns = CATEGORY_COLUMNS.flatMap((column) => {
    const list = answer.answers.find(
      (child): child is ListAnswer => child.type === "list" && child.role === column.role,
    );
    return list ? [{ ...column, list }] : [];
  });
  const rest = answer.answers.filter((child) => !columns.some((column) => column.list === child));
  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>{answer.label}</B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        {rest.length > 0 ? <Answers answers={rest} /> : null}
        <div className="flex flex-col gap-6 lg:flex-row">
          {columns.map((column) => (
            <div key={column.role} className={cn("w-full border-l-4 pl-4 lg:flex-1", column.border)}>
              <h4 className={cn("mb-4 font-medium", column.title)}>{column.list.label}</h4>
              <ul className="space-y-2">
                {column.list.items.map((item, index) => (
                  <li key={index} className="text-osce-body leading-relaxed text-b2c-text-secondary">
                    {column.bullet}
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function Answers({ answers }: { answers: AnswerView[] }) {
  return (
    <>
      {answers.map((answer, index) => (
        <Answer key={`${answer.label}-${index}`} answer={answer} />
      ))}
    </>
  );
}

/** One answer, by type first (its shape) and role second (how it reads). */
function Answer({ answer }: { answer: AnswerView }) {
  const critical = answer.role === "flag";
  switch (answer.type) {
    case "tag":
      return (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-osce-meta text-b2c-text-muted">{answer.label}</span>
          <Badge variant="accent">{answer.text}</Badge>
        </div>
      );
    case "text":
      if (answer.role === "evidence") {
        return (
          <blockquote className="border-l-2 border-b2c-border pl-3 text-osce-body italic text-b2c-text-secondary">
            &ldquo;{answer.text}&rdquo;
          </blockquote>
        );
      }
      if (answer.role === "explanation" || answer.role === "summary") {
        return (
          <p className="rounded-md bg-osce-accent-muted p-3 text-osce-body leading-relaxed text-b2c-text-secondary">
            {answer.text}
          </p>
        );
      }
      return (
        <div className={cn(critical && "rounded-md border border-osce-danger-border bg-osce-danger-bg p-3")}>
          <p className="text-osce-meta font-medium text-b2c-text-muted">{answer.label}</p>
          <p className={cn("text-osce-body", critical ? "text-osce-danger-text" : "text-b2c-text-secondary")}>
            {answer.text}
          </p>
        </div>
      );
    case "list": {
      const decoration = ROLE_ICON[answer.role];
      const Icon = decoration?.icon;
      return (
        <div className={cn(critical && "rounded-md border border-osce-danger-border bg-osce-danger-bg p-3")}>
          <p className={cn("mb-1.5 text-osce-meta font-semibold", critical ? "text-osce-danger-text" : "text-osce-ink-700")}>
            {answer.label}
          </p>
          <ul className="space-y-1.5">
            {answer.items.map((item, index) => (
              <li key={index} className="flex gap-2 text-osce-body leading-relaxed text-b2c-text-secondary">
                {Icon ? (
                  <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", decoration.className)} aria-hidden />
                ) : (
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-b2c-text-muted" aria-hidden />
                )}
                <span className={cn(answer.role === "evidence" && "italic")}>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      );
    }
    case "group":
      return (
        <div className="rounded-lg border border-b2c-border-light bg-b2c-surface-muted p-4">
          <p className="mb-3 text-osce-body font-semibold text-osce-ink-900">{answer.label}</p>
          <div className="space-y-3">
            <Answers answers={answer.answers} />
          </div>
        </div>
      );
    case "records":
      return (
        <div>
          <p className="mb-2 text-osce-meta font-semibold text-osce-ink-700">{answer.label}</p>
          <div className="grid gap-3 md:grid-cols-2">
            {answer.records.map((record, index) => (
              <div key={index} className="space-y-2 rounded-lg border border-b2c-border-light bg-b2c-surface-muted p-4">
                <Answers answers={record} />
              </div>
            ))}
          </div>
        </div>
      );
  }
}
