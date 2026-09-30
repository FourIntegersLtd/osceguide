/**
 * Give the local library stations with a real document behind them.
 *
 * The seed (`api/scripts/seed_platform.py`) authors the four exams
 * and their rubrics; the stations come from a migration of the legacy
 * Firestore collections, which nobody runs locally. What is left is a handful
 * of stations carrying a `patient_information` block and nothing else — enough
 * to run a consultation, and not enough to see the reading period or the
 * management plan, which are the two screens most of the station work is.
 *
 * So this writes one full station per exam, shaped exactly like the legacy
 * documents (`frontend/src/b2c/types/station`). Idempotent by title.
 *
 *   node scripts/seed-dev-stations.mjs --email you@example.com --password ...
 *   node scripts/seed-dev-stations.mjs --clean --title "Hip pain in a runner"
 *
 * The account must be a platform admin: these are platform-library stations.
 *
 * `--clean` runs `clean-dev-library.mjs` with `--dev` plus any `--title` flags
 * you pass (archives published junk; does not delete rows).
 */

import { signInWithPassword } from "./admin-totp.mjs";

const API = process.env.PLATFORM_API_URL ?? "http://127.0.0.1:8002";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

const EMAIL = arg("email", "admin@osceguide.com");
const PASSWORD = arg("password", "correct horse battery");

async function call(path, { method = "GET", body, token } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(`${method} ${path} → ${response.status} ${text.slice(0, 200)}`);
  }
  return parsed;
}

const SCA = {
  title: "Dev · Chest pain in a 54-year-old",
  exam_code: "sca",
  content: {
    station_name: "Dev · Chest pain in a 54-year-old",
    doctor_information: {
      patient_biodata: "Mr Ade Bello, 54, teacher",
      recent_notes: [
        "Seen by a colleague three weeks ago with indigestion",
        "Blood pressure 148/92 at that visit, not rechecked",
      ],
      current_medications: ["Ramipril 5mg once daily", "Omeprazole 20mg once daily"],
      past_medical_history: ["Hypertension, diagnosed 2021", "Ex-smoker, stopped 2019"],
      social_history: ["Lives with his wife", "Teaches secondary school", "Rarely drinks"],
      recent_investigations: ["ECG 3 weeks ago: sinus rhythm, no acute change"],
      photos: [],
    },
    patient_information: {
      patient_biodata: "Mr Ade Bello, 54, teacher",
      gender: "male",
      persona: "Anxious, talks quickly, minimises symptoms when asked directly.",
      opening_sentence: "Doctor, I keep getting this pain in my chest.",
      expanded_history:
        "Central tightness on exertion for three weeks, easing after a few minutes of rest. Last week it came on walking upstairs.",
      idea: ["Thinks it is his indigestion coming back"],
      concerns: ["His father died of a heart attack at 58"],
      expectation: ["Wants something stronger for the indigestion"],
    },
    management_plan: {
      explanation:
        "The history is exertional and relieved by rest, which points to stable angina rather than reflux.",
      differential_diagnosis: ["Stable angina", "Acute coronary syndrome", "GORD"],
      examination_findings: ["Blood pressure", "Heart sounds", "Peripheral pulses"],
      assessment: ["Risk factors", "Exercise tolerance", "Red flags for ACS"],
      further_investigations: ["ECG", "Bloods including troponin if pain at rest", "Lipids and HbA1c"],
      social_concerns: ["Worried about missing work", "His father's death at a similar age"],
      ice: ["Name the fear about his heart rather than waiting for him to raise it"],
      immediate_actions: ["Same-day assessment if pain at rest or increasing frequency"],
      pharmacological_treatment: ["Aspirin 75mg", "GTN spray as required", "Statin"],
      non_pharmacological_treatment: ["Cardiac rehabilitation referral", "Exercise advice"],
      health_education: ["How to use a GTN spray", "What to do if the pain does not settle"],
      follow_up: "Review in two weeks, sooner if symptoms change.",
      safety_netting:
        "Call 999 for pain at rest lasting more than 15 minutes, or pain with sweating or breathlessness.",
      additional_notes: "He has not connected his father's death to his own symptoms out loud.",
    },
  },
};

const PLAB = {
  title: "Dev · Explaining a new diagnosis of asthma",
  exam_code: "plab",
  content: {
    station_name: "Dev · Explaining a new diagnosis of asthma",
    doctor_information: {
      doctor_identity: "You are an FY2 in a general practice surgery.",
      patient_information: [
        "Miss Priya Nair, 22, student",
        "Spirometry last week confirmed asthma",
        "She has not been started on any inhaler yet",
      ],
      task_instructions:
        "Explain the diagnosis, agree a treatment plan and address her concerns. Do not examine her.",
    },
    patient_information: {
      patient_biodata: "Miss Priya Nair, 22",
      gender: "female",
      persona: "Quiet, worried about what this means for her sport.",
      opening_sentence: "They said the breathing test showed something?",
      idea: ["Thinks asthma means she will have to stop running"],
      concerns: ["Becoming dependent on an inhaler"],
      expectation: ["Wants to know whether it will go away"],
    },
    management_plan: {
      explanation: "Asthma is a long-term but very treatable narrowing of the airways.",
      immediate_actions: ["Start a preventer inhaler", "Teach inhaler technique"],
      health_education: ["A personal asthma action plan", "Recognising a worsening attack"],
      follow_up: "Review in six weeks with a symptom diary.",
      safety_netting: "Seek urgent help if the reliever is needed more than every four hours.",
    },
  },
};

const STATIONS = [SCA, PLAB];

async function runClean() {
  const { spawnSync } = await import("node:child_process");
  const { dirname, join } = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const root = join(dirname(fileURLToPath(import.meta.url)), "..");
  const extra = process.argv.filter((_, i, a) => a[i - 1] === "--title");
  const args = ["scripts/clean-dev-library.mjs", "--dev", ...extra.flatMap((t) => ["--title", t])];
  if (process.argv.includes("--dry-run")) args.push("--dry-run");
  const email = arg("email", EMAIL);
  const password = arg("password", PASSWORD);
  args.push("--email", email, "--password", password);
  const result = spawnSync(process.execPath, args, { stdio: "inherit", cwd: root });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

async function main() {
  if (process.argv.includes("--clean")) {
    await runClean();
    return;
  }

  const auth = await signInWithPassword(API, EMAIL, PASSWORD);
  const token = auth.access_token;

  for (const station of STATIONS) {
    const existing = await call(
      `/api/v1/stations?exam_code=${station.exam_code}&limit=100`,
      { token },
    ).catch(() => ({ items: [] }));
    if (existing.items?.some((row) => row.title === station.title)) {
      console.log(`· ${station.title} — already there`);
      continue;
    }

    const created = await call("/api/v1/platform/stations", {
      method: "POST",
      token,
      body: {
        title: station.title,
        exam_code: station.exam_code,
        content: station.content,
      },
    });
    await call(`/api/v1/platform/stations/${created.id}/versions/1/publish`, {
      method: "POST",
      token,
    });
    console.log(`✓ ${station.title}`);
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
