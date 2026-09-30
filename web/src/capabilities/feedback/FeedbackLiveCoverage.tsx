import { HiOutlineCheckCircle, HiOutlineEllipsisHorizontalCircle } from "react-icons/hi2";
import { productTokens } from "@/foundation/ui";

/** One checklist item the live examiner watched for, and whether it was heard. */
export interface CoverageEntry {
  id: string;
  label: string;
  covered: boolean;
  quote: string | null;
  seq: number;
}

const { b2cCard, b2cSectionTitle } = productTokens;

/**
 * What the live panel showed while the consultation was running.
 *
 * Shown beside the mark rather than as part of it. Coverage says what was
 * done; the RAG scores above say how well. The two can legitimately disagree —
 * covering something badly still covers it — so this is framed as a record of
 * the consultation, never as a score.
 */
export function FeedbackLiveCoverage({ coverage }: { coverage: CoverageEntry[] }) {
  if (coverage.length === 0) return null;

  const covered = coverage.filter((item) => item.covered).length;

  return (
    <section className={`${b2cCard} p-4 sm:p-5`}>
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className={b2cSectionTitle}>What you covered as you went</h2>
        <span className="text-osce-meta tabular-nums text-b2c-text-muted">
          {covered} of {coverage.length} fully
        </span>
      </div>
      <p className="mb-4 text-osce-meta leading-relaxed text-b2c-text-muted">
        Recorded live during the consultation, in the order you did them. This is a record of what
        you covered, not your mark.
      </p>

      <ul className="flex flex-col gap-2">
        {coverage.map((item) => {
          const Icon = item.covered ? HiOutlineCheckCircle : HiOutlineEllipsisHorizontalCircle;
          return (
            <li
              key={item.id}
              className={`flex items-start gap-2.5 rounded-osce-md border px-3 py-2.5 ${
                item.covered
                  ? "border-osce-success-border bg-osce-success-bg"
                  : "border-osce-warning-border bg-osce-warning-bg"
              }`}
            >
              <Icon
                className={`mt-0.5 h-5 w-5 shrink-0 ${
                  item.covered ? "text-osce-success-icon" : "text-osce-warning-icon"
                }`}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <p className="text-osce-data font-medium text-osce-ink-900">
                  {item.label}
                  {!item.covered && (
                    <span className="ml-1 font-normal text-b2c-text-muted"> · partly</span>
                  )}
                </p>
                {item.quote && (
                  <p className="mt-0.5 text-osce-meta italic leading-relaxed text-b2c-text-secondary">
                    &ldquo;{item.quote}&rdquo;
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
