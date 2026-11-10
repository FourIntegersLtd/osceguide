/** The "How it works" board: the curve, the three nodes and the illustrative text and figures inside the vignettes. Positions are in the 1200 x 780 desktop panel. */
export const HOW_PANEL = { width: 1200, height: 780 } as const;

export const HOW_CURVE = "M 0 700 C 110 700 150 660 220 660 C 390 660 470 530 640 530 C 810 530 880 400 1020 400 C 1090 400 1140 370 1200 360";
export const HOW_GRID_YS = [140, 280, 420, 560, 700] as const;

/** Node centres, as numbers on the curve, and the step's width (the last is wider so its heading stays on two lines). A step's text sits 64px above its node. */
export const HOW_NODES = [
  { n: "01", x: 220, y: 660, w: 300 },
  { n: "02", x: 640, y: 530, w: 300 },
  { n: "03", x: 1020, y: 400, w: 340 },
] as const;
export const HOW_STEP_GAP = 64;
/** Distance from a node's centre to its stem's top, and the node's radius. The stem is `HOW_STEM` tall. */
export const HOW_NODE_RADIUS = 24;
export const HOW_STEM = 38;
export const HOW_STEM_TOP = HOW_NODE_RADIUS + HOW_STEM;
/** Height of every vignette block above the marks card. */
export const VIGNETTE_H = 214;

export const HOW_LEGEND = "Your scores over time";

export const HOW_CASES = { label: "Cases", counts: [1, 3, 6], selected: 3 } as const;
export const HOW_DECK = { chip: "SCA", progress: "1 / 3" } as const;

export const HOW_CONSULT = {
  clock: "09:42",
  patient: "It started three days ago, doctor. It’s mostly when I climb the stairs.",
  doctor: "Can you tell me what the pain feels like?",
  /** Waveform bars: height in px and opacity. */
  wave: [
    [6, 0.5], [12, 0.7], [20, 1], [14, 0.8], [26, 1], [10, 0.6], [18, 0.9], [8, 0.5],
    [22, 1], [12, 0.7], [6, 0.5], [16, 0.8], [10, 0.6], [20, 1], [8, 0.5],
  ],
} as const;

export const HOW_MARKS = {
  title: "Your marks",
  chip: "Marked",
  domains: [
    { label: "Global skills", level: "Competent", percent: 72 },
    { label: "Tasks", level: "Developing", percent: 48 },
    { label: "Relating to others", level: "Competent", percent: 64 },
  ],
  athena: "Athena: let’s go over the moment you skipped the red flags.",
} as const;
