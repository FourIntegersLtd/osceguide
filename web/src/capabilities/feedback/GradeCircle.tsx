import { gradeWord } from "@/capabilities/feedback/feedbackWords";
import { toneVariant } from "@/capabilities/feedback/rubric";

const TONE_CLASSES: Record<ReturnType<typeof toneVariant>, string> = {
  danger: "bg-osce-danger-border text-osce-danger",
  warning: "bg-osce-warning-border text-osce-warning-text",
  success: "bg-osce-success-border text-osce-success-text",
  neutral: "bg-osce-canvas text-osce-ink-700",
};

/**
 * A scale grade in a disc: the letter, coloured by the tone the rubric's
 * display gives it.
 *
 * The colour comes from the tone (good, fair, poor...), never from the letter,
 * so a rubric whose scale is "Excellent / Pass / Fail" is coloured by the same
 * rule as one whose scale is G / A / R.
 */
export function GradeCircle({ grade, tone }: { grade: string; tone: string | null }) {
  const label = `Graded ${gradeWord(grade, tone)}`;
  return (
    <span
      title={label}
      aria-label={label}
      role="img"
      className={`mr-2 inline-flex h-7 min-w-7 shrink-0 items-center justify-center rounded-full px-1.5 text-osce-body font-semibold ${TONE_CLASSES[toneVariant(tone)]}`}
    >
      {grade}
    </span>
  );
}
