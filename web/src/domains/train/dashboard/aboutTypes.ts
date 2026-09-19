/**
 * The shape of an "about" modal, and the one piece of copy three exams share.
 *
 * Split from `aboutCopy.ts` only to keep both files short; the table of
 * sentences is next door.
 */

export type AboutMarker = "success" | "danger" | "plain" | "threshold" | "swatch";

export interface AboutItem {
  marker: AboutMarker;
  /** For `swatch`: which domain's colour to show, looked up in the exam config. */
  swatchFor?: string;
  title: string;
  description: string;
}

export interface AboutContent {
  title: string;
  description: string;
  sectionTitle: string;
  sectionTone?: "sky" | "amber";
  items: AboutItem[];
  callout?: { label: string; text: string };
}

export type AboutKey = "summary" | "domain" | "trend";

export type ExamAbout = Record<AboutKey, AboutContent>;

export const LEARNING_JOURNEY = (exam: string, strong: string): AboutContent => ({
  title: "Your learning journey",
  description: `This section shows your progress across all completed ${exam} stations. Remember, every station is a learning opportunity on your path to success.`,
  sectionTitle: "What the scores mean",
  sectionTone: "sky",
  items: [
    {
      marker: "success",
      title: "Strong performance",
      description: strong,
    },
    {
      marker: "danger",
      title: "Growth opportunities",
      description:
        "Stations with room for development. These are valuable learning experiences that guide your focused preparation and skill building.",
    },
  ],
  callout: {
    label: "Remember",
    text: "Every expert was once a beginner. Your performance today is the foundation for tomorrow's success. Focus on progress, not perfection.",
  },
});
