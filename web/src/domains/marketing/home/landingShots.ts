/** The captures of the running app used on `/`: flat, no browser chrome, 2x. Display box is 1040x800. */
export type LandingShot = { src: string; width: number; height: number; alt: string };

const BOX = { width: 1040, height: 800 } as const;
const DIR = "/images/landing";

export const LANDING_SHOTS = {
  choose: {
    src: `${DIR}/step-choose.png`,
    ...BOX,
    alt: "The Practice page, Setup tab, showing 1 of 3 free stations completed, a Session setup form with a session name and number of stations, a Create session button, and a Before you start checklist.",
  },
  consult: {
    src: `${DIR}/step-consult.png`,
    ...BOX,
    alt: "A consultation in progress: tabs for Reading time, Consultation, Management and Feedback, the patient's speaking button, and the transcript so far starting 'Hello Mr Reid, my name is Dr Walker'.",
  },
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
  institutions: {
    src: "/images/b2b/b2b-dashboard.png",
    width: 2458,
    height: 1704,
    alt: "The institutions dashboard: a Hello page with sessions, trainees and stations at a glance, an Organisation list (Team, Trainees, Stations, Templates) and a Before you go live checklist at 4 of 5.",
  },
  poster: {
    src: `${DIR}/hero-poster.png`,
    ...BOX,
    alt: "",
  },
} as const satisfies Record<string, LandingShot>;

export const HERO_CLIP_SOURCES = [
  { src: `${DIR}/hero-clip.webm`, type: "video/webm" },
  { src: `${DIR}/hero-clip.mp4`, type: "video/mp4" },
] as const;

export const HERO_CLIP_LABEL =
  "A practice station in the app: setting up a session, the reading screen with its clock, the marked feedback report and the debrief. No sound.";
