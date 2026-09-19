import type { Rag } from "@/capabilities/feedback/model";

const GRADE_CLASSES: Record<Rag, string> = {
  R: "bg-osce-danger-border text-osce-danger",
  A: "bg-osce-warning-border text-osce-warning-text",
  G: "bg-osce-success-border text-osce-success-text",
};

/**
 * The red/amber/green disc.
 *
 * Used by every framework's feedback, which is why it sits beside the
 * normaliser rather than inside one screen: the letter is the product's
 * vocabulary for a grade and a second spelling of it would read as a second
 * meaning.
 */
export function GradeCircle({ grade }: { grade: Rag }) {
  return (
    <span
      className={`inline-flex items-center justify-center w-7 h-7 rounded-full ${GRADE_CLASSES[grade]} text-osce-body font-semibold mr-2`}
    >
      {grade}
    </span>
  );
}
