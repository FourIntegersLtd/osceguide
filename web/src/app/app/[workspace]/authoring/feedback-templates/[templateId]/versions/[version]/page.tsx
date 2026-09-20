import { redirect } from "next/navigation";

/** Feedback templates were merged into rubric versions (`marking_layout`). */
export default function LegacyFeedbackTemplateEditPage() {
  redirect("../../../../rubrics");
}
