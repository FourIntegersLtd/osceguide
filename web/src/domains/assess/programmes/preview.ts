/**
 * Sample data for the programme screens, which have no API yet.
 *
 * Each type is the response the screen needs from a route that does not exist;
 * each constant is one made-up example of it, so the screen can be seen and
 * reviewed. When a route lands, its screen swaps the import for `useAsync`
 * over an `api.ts` call and the constant is deleted. Every screen that reads
 * from here shows `PreviewNotice`, so nobody takes these people for real ones.
 */
import type { ProgrammePurpose } from "@/domains/assess/programmes/purposes";

export interface ProgrammeSummary {
  id: string;
  name: string;
  purpose: ProgrammePurpose;
  people: number;
  whereItIs: string;
  status: string;
}

export interface ProgrammeStage {
  figure: string;
  detail: string;
}

export interface ProgrammeStation {
  title: string;
  meta: string;
}

interface ProgrammeBase {
  id: string;
  name: string;
  summary: string;
  stages: readonly [ProgrammeStage, ProgrammeStage, ProgrammeStage];
}

export interface PlacementProgramme extends ProgrammeBase {
  purpose: "placement";
  total: number;
  students: { name: string; email: string; stage: string; stations: number; readiness: string }[];
  firstContact: { date: string; note: string };
  sessions: { name: string; when: string; booked: boolean }[];
  stations: ProgrammeStation[];
}

export interface RecruitmentCandidate {
  name: string;
  status: string;
  /** Null until the findings are ready. */
  findings: { green: number; amber: number; red: number } | null;
  review: string;
  packReady: boolean;
}

export interface RecruitmentProgramme extends ProgrammeBase {
  purpose: "recruitment";
  candidates: RecruitmentCandidate[];
  spotlight: { name: string; didWell: string[]; toImprove: string[]; notDone: string[] };
  howCandidatesJoin: string[];
  stations: ProgrammeStation[];
}

export interface OnboardingProgramme extends ProgrammeBase {
  purpose: "onboarding";
  modules: { title: string; stage: string; completion: number }[];
  starters: { name: string; started: string; stage: string; supervisor: string; signOff: string }[];
  signedOff: { ready: number; total: number };
  waiting: { name: string; detail: string }[];
}

export interface CpdProgramme extends ProgrammeBase {
  purpose: "cpd";
  total: number;
  updates: { title: string; meta: string; completion: number }[];
  staff: { name: string; role: string; hours: string; lastPractice: string; certificate: boolean }[];
}

export type ProgrammeDetailData =
  | PlacementProgramme
  | RecruitmentProgramme
  | OnboardingProgramme
  | CpdProgramme;

export const PREVIEW_PROGRAMMES: ProgrammeSummary[] = [
  { id: "st3-2026", name: "ST3 2026", purpose: "exam_preparation", people: 42, whereItIs: "Mock SCA, cohort B today", status: "Running" },
  { id: "st2-2026", name: "ST2 2026", purpose: "exam_preparation", people: 30, whereItIs: "Practising stations", status: "Active" },
  { id: "year-4-gp-placement", name: "Year 4 GP placement", purpose: "placement", people: 24, whereItIs: "Practise safely", status: "Active" },
  { id: "practice-nurse-band-6", name: "Practice Nurse, Band 6", purpose: "recruitment", people: 5, whereItIs: "Interviews from 13 Oct", status: "Open" },
  { id: "international-gps-2026", name: "International GPs, 2026 intake", purpose: "onboarding", people: 8, whereItIs: "Adapt communication", status: "Active" },
  { id: "clinical-staff-2026", name: "Clinical staff 2026", purpose: "cpd", people: 64, whereItIs: "2 guidance updates live", status: "Active" },
];

export const PREVIEW_PROGRAMME_DETAILS: ProgrammeDetailData[] = [
  {
    id: "year-4-gp-placement",
    purpose: "placement",
    name: "Year 4 GP placement",
    summary:
      "24 students getting ready for their first week in practice. Practice only: nothing here is marked for the record.",
    stages: [
      { figure: "24 started", detail: "Short, low-stakes stations with an AI patient" },
      { figure: "17 practising", detail: "Tutor-led sessions with a supervisor listening in" },
      { figure: "9 ready", detail: "Readiness check before the first patient" },
    ],
    total: 24,
    students: [
      { name: "Amara Osei", email: "a.osei@student.ac.uk", stage: "Prepare for real clinical encounters", stations: 9, readiness: "Ready" },
      { name: "Sam Idowu", email: "s.idowu@student.ac.uk", stage: "Practise safely", stations: 5, readiness: "On track" },
      { name: "Josh Patel", email: "j.patel@student.ac.uk", stage: "Practise safely", stations: 6, readiness: "Nearly ready" },
      { name: "Leah Morgan", email: "l.morgan@student.ac.uk", stage: "Build confidence", stations: 2, readiness: "Needs support" },
    ],
    firstContact: { date: "3 November", note: "4 weeks away · 9 of 24 students ready" },
    sessions: [
      { name: "Group practice, cohort A", when: "Thu 9 Oct · 14:00 · Dr K. Bell listening in", booked: true },
      { name: "Group practice, cohort B", when: "Thu 16 Oct · 14:00", booked: false },
    ],
    stations: [
      { title: "Taking a history from a worried parent", meta: "Build confidence · 8 min" },
      { title: "Explaining a blood test result", meta: "Practise safely · 10 min" },
      { title: "Escalating a deteriorating patient", meta: "Practise safely · 10 min" },
      { title: "Consent for a procedure", meta: "Readiness check · 10 min" },
    ],
  },
  {
    id: "practice-nurse-band-6",
    purpose: "recruitment",
    name: "Practice Nurse, Band 6",
    summary:
      "Candidates sit three role-relevant stations before interview. You get what each one did well, what needs improving and what they missed, to inform the interview. The decision stays with your panel.",
    stages: [
      { figure: "5 invited", detail: "4 have sat the stations" },
      { figure: "3 stations", detail: "Asthma review, telephone triage, wound care" },
      { figure: "2 packs ready", detail: "Interviews from 13 October" },
    ],
    candidates: [
      { name: "Hannah Price", status: "Sat 3 Oct", findings: { green: 9, amber: 2, red: 1 }, review: "Reviewed", packReady: true },
      { name: "Ruth Adeyemi", status: "Sat 4 Oct", findings: { green: 7, amber: 4, red: 1 }, review: "In review", packReady: false },
      { name: "Marcus Lee", status: "Sat 3 Oct", findings: { green: 5, amber: 4, red: 3 }, review: "Reviewed", packReady: true },
      { name: "Ana Silva", status: "Sat 5 Oct", findings: null, review: "Processing", packReady: false },
      { name: "Kofi Mensah", status: "Invited 1 Oct", findings: null, review: "Invited", packReady: false },
    ],
    spotlight: {
      name: "Hannah Price",
      didWell: [
        "Checked inhaler technique and asked her to show it",
        "Explored what worried her about steroids",
        "Clear, calm telephone triage questions",
        "Explained wound care in plain words",
      ],
      toImprove: [
        "Asthma action plan offered, not agreed with the patient",
        "Safety-net named symptoms but no time frame",
      ],
      notDone: ["Did not ask about smoking or vaping"],
    },
    howCandidatesJoin: [
      "A link in their invitation email. No OSCE Guide account needed.",
      "Three role-relevant stations, about 40 minutes, any time before 10 Oct.",
      "They do not see the findings.",
    ],
    stations: [
      { title: "Asthma review with an anxious patient", meta: "Structured assessment · 12 min" },
      { title: "Telephone triage", meta: "Role-relevant scenario · 12 min" },
      { title: "Wound care advice", meta: "Role-relevant scenario · 12 min" },
    ],
  },
  {
    id: "international-gps-2026",
    purpose: "onboarding",
    name: "International GPs, 2026 intake",
    summary:
      "Eight GPs new to NHS general practice. They practise UK consultation expectations with an AI patient, and a supervisor signs off each stage.",
    stages: [
      { figure: "8 of 8", detail: "Know how an NHS consultation is expected to run" },
      { figure: "6 of 8", detail: "ICE, shared decisions, safety-netting" },
      { figure: "2 of 8", detail: "Signed off for independent clinics" },
    ],
    modules: [
      { title: "How an NHS GP consultation runs", stage: "Understand expectations", completion: 100 },
      { title: "Ideas, concerns and expectations", stage: "Adapt communication", completion: 88 },
      { title: "Shared decisions and consent", stage: "Adapt communication", completion: 63 },
      { title: "Safety-netting and follow-up", stage: "Adapt communication", completion: 50 },
      { title: "Telephone and remote consultations", stage: "Transition into NHS practice", completion: 38 },
      { title: "Referrals and working with the practice team", stage: "Transition into NHS practice", completion: 25 },
    ],
    starters: [
      { name: "Dr Aisha Rahman", started: "Started 1 Sep", stage: "Transition into NHS practice", supervisor: "Dr K. Bell", signOff: "Signed off" },
      { name: "Dr Meera Nair", started: "Started 1 Sep", stage: "Transition into NHS practice", supervisor: "Dr K. Bell", signOff: "Ready for sign-off" },
      { name: "Dr Yusuf Bello", started: "Started 8 Sep", stage: "Adapt communication", supervisor: "Dr S. Okafor", signOff: "Stage 1 signed off" },
      { name: "Dr Carlos Ruiz", started: "Started 29 Sep", stage: "Understand expectations", supervisor: "Dr S. Okafor", signOff: "In progress" },
    ],
    signedOff: { ready: 2, total: 8 },
    waiting: [{ name: "Dr Meera Nair", detail: "Stage 3 sign-off · 6 of 6 modules" }],
  },
  {
    id: "clinical-staff-2026",
    purpose: "cpd",
    name: "Clinical staff 2026",
    summary:
      "64 clinicians. When guidance changes, a short set of stations follows, and completed practice is logged for appraisal.",
    stages: [
      { figure: "2 live", detail: "Guidance updates this quarter" },
      { figure: "5 stations", detail: "Generated from those updates" },
      { figure: "212 h", detail: "CPD logged by the team this year" },
    ],
    total: 64,
    updates: [
      { title: "Sepsis recognition in primary care", meta: "Guidance update · 3 stations · published 15 Sep", completion: 64 },
      { title: "Remote prescribing safeguards", meta: "Guidance update · 2 stations · published 29 Sep", completion: 19 },
      { title: "Safeguarding conversations", meta: "Annual · 4 stations · closed 31 Aug", completion: 100 },
    ],
    staff: [
      { name: "Dr Kate Bell", role: "GP partner", hours: "6.5 h", lastPractice: "Today", certificate: true },
      { name: "Mr Raj Patel", role: "Advanced nurse practitioner", hours: "4.0 h", lastPractice: "Yesterday", certificate: true },
      { name: "Jo Okonkwo", role: "Practice pharmacist", hours: "1.5 h", lastPractice: "12 Sep", certificate: true },
      { name: "Dr Dan Taylor", role: "Salaried GP", hours: "0 h", lastPractice: "Not started", certificate: false },
    ],
  },
];

/** The trainee's own view of a programme they are in. */
export interface MyProgrammeData {
  id: string;
  name: string;
  summary: string;
  stages: { title: string; state: "signed_off" | "current" | "upcoming"; detail: string }[];
  modules: { title: string; done: boolean; band: "competent" | "developing" | "development" | null; meta: string }[];
  supervisor: { name: string; role: string; visibility: string };
}

export const PREVIEW_MY_PROGRAMME: MyProgrammeData = {
  id: "international-gps-2026",
  name: "International GPs, 2026 intake",
  summary:
    "Your route into NHS general practice. Practise each module with an AI patient; your supervisor signs off each stage.",
  stages: [
    { title: "Understand expectations", state: "signed_off", detail: "Signed off by Dr K. Bell on 15 Sep" },
    { title: "Adapt communication", state: "signed_off", detail: "Signed off by Dr K. Bell on 26 Sep" },
    { title: "Transition into NHS practice", state: "current", detail: "4 of 6 modules, then your final sign-off" },
  ],
  modules: [
    { title: "How an NHS GP consultation runs", done: true, band: "competent", meta: "Done" },
    { title: "Ideas, concerns and expectations", done: true, band: "competent", meta: "Done" },
    { title: "Shared decisions and consent", done: true, band: "developing", meta: "Done" },
    { title: "Safety-netting and follow-up", done: true, band: "competent", meta: "Done" },
    { title: "Telephone and remote consultations", done: false, band: null, meta: "2 stations · about 25 min" },
    { title: "Referrals and working with the practice team", done: false, band: null, meta: "2 stations · about 25 min" },
  ],
  supervisor: {
    name: "Dr Kate Bell",
    role: "Educational supervisor",
    visibility:
      "Your practice in this programme is visible to Dr Bell. Practice you do on your own stays private unless you share a station.",
  },
};
