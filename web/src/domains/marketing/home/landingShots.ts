/** The captures of the running app used on `/`: 2x files, 1040x800. */
export type LandingShot = { src: string; width: number; height: number; alt: string };

const BOX = { width: 1040, height: 800 } as const;
const DIR = "/images/landing";

export const LANDING_SHOTS = {
  marked: {
    src: `${DIR}/step-marked.png`,
    ...BOX,
    alt: "The learner dashboard: 62% of assessed marks now meet the competent standard, Domain performance bars (Global skills 71%, Tasks 55%, Relating to others 64%), an eight-week trend and a What to work on list.",
  },
  feedback: {
    src: `${DIR}/feedback.png`,
    ...BOX,
    alt: "A marked station reading Your mark: 62% of competencies graded Good, with three domain cards, each listing competencies with a Good or Fair badge and a quoted line from the transcript.",
  },
  debrief: {
    src: `${DIR}/debrief.png`,
    ...BOX,
    alt: "The Debrief details page with a narrative summary of a telephone consultation, a Key insights list and a numbered Action plan.",
  },
  extraTime: {
    src: `${DIR}/extra-time.png`,
    ...BOX,
    alt: "Settings, Preferences tab, with switches for AI training consent, Extra reading time, and an email when a colleague is waiting, and a Start button for Athena onboarding.",
  },
} as const satisfies Record<string, LandingShot>;
