/*
 * The vocabulary of the product-feedback form, shared by the form and its
 * field widgets. The retiring client posted this composition to
 * `/api/create_message`; `POST /site/messages` files it as `product_feedback`
 * and the body keeps the old shape, which is what the team reading the inbox
 * expects.
 */

export type ProductFeedbackSource = "session" | "milestone" | "contact";

export type TestimonialPermission = "yes_with_name" | "yes_anonymous" | "no";

export const TESTIMONIAL_LABELS: Record<TestimonialPermission, string> = {
  yes_with_name: "Yes, with my name",
  yes_anonymous: "Yes, anonymously",
  no: "No",
};

export const TESTIMONIAL_OPTIONS: {
  value: TestimonialPermission;
  label: string;
  compactLabel: string;
}[] = [
  { value: "yes_with_name", label: "Yes, with my name", compactLabel: "Yes, named" },
  { value: "yes_anonymous", label: "Yes, anonymously", compactLabel: "Yes, anonymous" },
  { value: "no", label: "No", compactLabel: "No" },
];

/** The retiring client's message composition, line for line. */
export function composeFeedbackBody(input: {
  name: string;
  email: string;
  rating: number;
  testimonialPermission: TestimonialPermission;
  source: ProductFeedbackSource;
  examCode?: string;
  experience: string;
}): string {
  const lines = [
    `Name: ${input.name || "(not provided)"}`,
    `Email: ${input.email}`,
    `Rating: ${input.rating}/5`,
    `Testimonial permission: ${TESTIMONIAL_LABELS[input.testimonialPermission]}`,
    `Source: ${input.source}`,
    input.examCode ? `App: ${input.examCode}` : null,
    "",
    "Experience:",
    input.experience || "(No written comment)",
  ].filter((line): line is string => line !== null);
  return lines.join("\n");
}
