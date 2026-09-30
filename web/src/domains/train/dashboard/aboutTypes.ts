/**
 * The shape of an "about" modal. The sentences are built in `aboutCopy.ts`
 * from the rubric's display, so every exam's modals explain its own scale.
 */

export type AboutMarker = "success" | "danger" | "plain" | "threshold" | "swatch";

export interface AboutItem {
  marker: AboutMarker;
  /** For `swatch`: the colour the chart draws this item in. */
  color?: string;
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
