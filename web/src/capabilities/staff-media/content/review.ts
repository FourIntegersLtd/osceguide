/**
 * The checks stored on a spoken item's `content.review`, and the edits a
 * member of staff makes in answer to them.
 *
 * The server decides whether a script may be voiced (`script_not_checked`).
 * `isChecked` mirrors its rule so the screen can say so before the click: the
 * lines voicing would speak must be exactly the lines that were last checked.
 */

type Content = Record<string, unknown>;

export type Evidence = {
  kind: "guideline" | "web";
  source: string;
  section: string;
  page: number | null;
  url: string | null;
  quote: string;
};

export type FactVerdict =
  | "supported"
  | "contradicted"
  | "not_found"
  | "conflict"
  | "not_checked";

export type FactClaim = {
  id: string;
  /** The slide of a deck the claim sits on; null for a summary or podcast. */
  slide: number | null;
  claim: string;
  verdict: FactVerdict;
  why: string;
  checked: string[];
  evidence: Evidence[];
  /** `old` is null when the words to replace could not be pinned down. */
  suggestion: { old: string | null; new: string } | null;
  /** Set here, by the reader: what they did with the suggestion. */
  decision?: "accepted" | "dismissed";
};

export type ScriptIssue = {
  part: "slide" | "framing" | "deck" | "script";
  slide: number | null;
  line: number;
  kind: string;
  quote: string;
  why: string;
  fix: string;
};

export type ScriptChange = {
  part: "slide" | "framing" | "script";
  slide: number | null;
  line: number;
  before: string;
  after: string;
  kind: string;
  why: string;
};

export type Review = {
  facts: { checked_at: string; claims: FactClaim[] } | null;
  script: {
    checked_at: string | null;
    lines: string[];
    issues: ScriptIssue[];
    changes: ScriptChange[];
  } | null;
  error: { step: string; message: string } | null;
};

/** One run of lines that are spoken together: a slide, the framing, or the dialogue. */
export type ScriptGroup = {
  part: "slide" | "framing" | "script";
  slide: number | null;
  label: string;
  lines: { speaker: string | null; text: string }[];
};

const SPOKEN_KINDS = ["slide_deck", "summary", "podcast"];

export function isSpokenKind(kind: string): boolean {
  return SPOKEN_KINDS.includes(kind);
}

function record(value: unknown): Content | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Content)
    : null;
}

function records(value: unknown): Content[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry: unknown): Content[] => {
    const fields = record(entry);
    return fields ? [fields] : [];
  });
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function reviewOf(content: Content): Review {
  const review = record(content.review) ?? {};
  const facts = record(review.facts);
  const script = record(review.script);
  const error = record(review.error);
  return {
    facts: facts
      ? {
          checked_at: text(facts.checked_at),
          claims: records(facts.claims) as unknown as FactClaim[],
        }
      : null,
    script: script
      ? {
          checked_at: text(script.checked_at) || null,
          lines: Array.isArray(script.lines) ? script.lines.map(String) : [],
          issues: records(script.issues) as unknown as ScriptIssue[],
          changes: records(script.changes) as unknown as ScriptChange[],
        }
      : null,
    error: error
      ? { step: text(error.step), message: text(error.message) }
      : null,
  };
}

/** A `Ben: …` / `Michelle: …` script as its turns, the way the server splits it. */
export function splitScript(script: string): { speaker: string; text: string }[] {
  const marked = script.replace(
    /^\s*\**(ben|michelle)\**\s*:\**/gim,
    (_match, name: string) =>
      `\n${name.charAt(0).toUpperCase()}${name.slice(1).toLowerCase()}:`,
  );
  const parts = `\n${marked}`.split(/\n+(Ben|Michelle):[ \t]*/);
  const turns: { speaker: string; text: string }[] = [];
  for (let index = 1; index < parts.length - 1; index += 2) {
    const line = (parts[index + 1] ?? "")
      .split(/\s+/)
      .filter(Boolean)
      .join(" ")
      .replace(/["“”]/g, "")
      .trim();
    if (line) turns.push({ speaker: parts[index] ?? "", text: line });
  }
  return turns;
}

function narrationLines(slide: Content): string[] {
  const narration = record(slide.narration);
  if (!narration || !Array.isArray(narration.items)) return [];
  return [text(narration.intro), ...narration.items.map(String)];
}

function framingLines(plan: Content | null): string[] {
  if (!plan) return [];
  return [
    ...records(plan.sections).map((entry) => text(entry.line)),
    text(plan.recap_intro),
    ...records(plan.takeaways).map((entry) => text(entry.line)),
    text(plan.signoff),
  ];
}

/** What is said, grouped the way it is read: empty until all of it is written. */
export function scriptGroups(kind: string, content: Content): ScriptGroup[] {
  if (kind !== "slide_deck") {
    const lines = splitScript(text(content.script));
    return lines.length > 0
      ? [{ part: "script", slide: null, label: "Dialogue", lines }]
      : [];
  }
  const slides = records(content.slides);
  const framing = framingLines(record(content.presentation));
  const perSlide = slides.map(narrationLines);
  if (
    slides.length === 0 ||
    framing.length === 0 ||
    perSlide.some((lines) => lines.length === 0)
  )
    return [];
  const spoken = (lines: string[]) =>
    lines.map((line) => ({ speaker: null, text: line }));
  return [
    ...slides.map((slide, index): ScriptGroup => ({
      part: "slide",
      slide: index + 1,
      label: `Slide ${index + 1}: ${text(slide.title)}`,
      lines: spoken(perSlide[index] ?? []),
    })),
    {
      part: "framing",
      slide: null,
      label: "Section cards, recap and sign-off",
      lines: spoken(framing),
    },
  ];
}

/** Every line voicing would speak, in the order and form the server compares. */
export function spokenLines(kind: string, content: Content): string[] {
  return scriptGroups(kind, content).flatMap((group) =>
    group.lines.map((line) =>
      line.speaker ? `${line.speaker}: ${line.text}` : line.text,
    ),
  );
}

export function isChecked(kind: string, content: Content): boolean {
  const checked = reviewOf(content).script?.lines ?? null;
  const spoken = spokenLines(kind, content);
  return (
    checked !== null &&
    spoken.length > 0 &&
    spoken.length === checked.length &&
    spoken.every((line, index) => line === checked[index])
  );
}

function setFraming(plan: Content, index: number, value: string): Content {
  const sections = records(plan.sections);
  const takeaways = records(plan.takeaways);
  if (index < sections.length) {
    return {
      ...plan,
      sections: sections.map((entry, at) =>
        at === index ? { ...entry, line: value } : entry,
      ),
    };
  }
  if (index === sections.length) return { ...plan, recap_intro: value };
  const takeaway = index - sections.length - 1;
  if (takeaway < takeaways.length) {
    return {
      ...plan,
      takeaways: takeaways.map((entry, at) =>
        at === takeaway ? { ...entry, line: value } : entry,
      ),
    };
  }
  return { ...plan, signoff: value };
}

/** `content` with one spoken line replaced; `line` counts from 1 within its group. */
export function setScriptLine(
  content: Content,
  group: ScriptGroup,
  line: number,
  value: string,
): Content {
  if (group.part === "script") {
    const turns = group.lines.map((turn, index) =>
      `${turn.speaker}: ${index === line - 1 ? value : turn.text}`,
    );
    return { ...content, script: turns.join("\n\n") };
  }
  if (group.part === "framing") {
    const plan = record(content.presentation) ?? {};
    return { ...content, presentation: setFraming(plan, line - 1, value) };
  }
  const slides = Array.isArray(content.slides) ? content.slides : [];
  return {
    ...content,
    slides: slides.map((entry, index) => {
      const slide = record(entry);
      const narration = slide ? record(slide.narration) : null;
      if (!slide || !narration || index !== (group.slide ?? 0) - 1) return entry;
      const items = Array.isArray(narration.items) ? narration.items : [];
      return {
        ...slide,
        narration:
          line === 1
            ? { ...narration, intro: value }
            : {
                ...narration,
                items: items.map((item, at) => (at === line - 2 ? value : item)),
              },
      };
    }),
  };
}

/** Every string under `value` with `old` swapped for `next`; what was spoken is left alone. */
function replaced(value: unknown, old: string, next: string, key = ""): unknown {
  if (key === "review" || key === "narration" || key === "presentation") return value;
  if (typeof value === "string") return value.split(old).join(next);
  if (Array.isArray(value)) return value.map((entry) => replaced(entry, old, next));
  const fields = record(value);
  if (!fields) return value;
  return Object.fromEntries(
    Object.entries(fields).map(([name, entry]) => [
      name,
      replaced(entry, old, next, name),
    ]),
  );
}

function decided(
  content: Content,
  claimId: string,
  decision: "accepted" | "dismissed",
): Content {
  const review = record(content.review) ?? {};
  const facts = record(review.facts) ?? {};
  const claims = records(facts.claims).map((claim) =>
    claim.id === claimId ? { ...claim, decision } : claim,
  );
  return { ...content, review: { ...review, facts: { ...facts, claims } } };
}

/**
 * `content` with a claim's suggested correction made, in the slide it sits on
 * (or everywhere, for a summary or podcast). `wording` is what to put in its
 * place: the suggestion, or the reader's own edit of it.
 */
export function acceptSuggestion(
  content: Content,
  claim: FactClaim,
  wording: string,
): Content {
  const old = claim.suggestion?.old;
  if (!old) return content;
  const slides = Array.isArray(content.slides) ? content.slides : null;
  const corrected =
    claim.slide !== null && slides
      ? {
          ...content,
          slides: slides.map((slide, index) =>
            index === (claim.slide ?? 0) - 1 ? replaced(slide, old, wording) : slide,
          ),
        }
      : (replaced(content, old, wording) as Content);
  return decided(corrected, claim.id, "accepted");
}

export function dismissSuggestion(content: Content, claim: FactClaim): Content {
  return decided(content, claim.id, "dismissed");
}

export type StepId = "draft" | "facts" | "script" | "voice";

export type ReviewStep = {
  id: StepId;
  label: string;
  /** `attention` is a step that was done and now needs the reader again. */
  state: "todo" | "attention" | "done";
  note: string;
};

const VOICED_FIELD: Record<string, string> = {
  slide_deck: "final_video_url",
  summary: "podcast_url",
  podcast: "audio_url",
};

function hasDraft(kind: string, content: Content): boolean {
  if (kind === "slide_deck") return records(content.slides).length > 0;
  return Object.entries(content).some(
    ([name, value]) =>
      name !== "review" &&
      name !== "status" &&
      !name.endsWith("_url") &&
      (Array.isArray(value) ? value.length > 0 : text(value).trim() !== ""),
  );
}

/** A claim the reader still has to rule on: the sources say it is wrong, or disagree. */
export function needsRuling(claim: FactClaim): boolean {
  return (
    (claim.verdict === "contradicted" || claim.verdict === "conflict") &&
    !claim.decision
  );
}

/** The four steps from a brief to a voiced item, each with where it stands. */
export function reviewSteps(kind: string, content: Content): ReviewStep[] {
  const review = reviewOf(content);
  const claims = review.facts?.claims ?? [];
  const open = claims.filter(needsRuling).length;
  const written = scriptGroups(kind, content).length > 0;
  const checked = isChecked(kind, content);
  const flagged = review.script?.issues.length ?? 0;
  const status = text(content.status);
  const voiced =
    text(content[VOICED_FIELD[kind] ?? ""]).trim() !== "" &&
    (status === "" || status === "completed");
  return [
    {
      id: "draft",
      label: "Draft",
      state: hasDraft(kind, content) ? "done" : "todo",
      note: hasDraft(kind, content) ? "Written" : "Nothing written yet",
    },
    {
      id: "facts",
      label: "Check facts",
      state: !review.facts ? "todo" : open > 0 ? "attention" : "done",
      note: !review.facts
        ? "Not checked"
        : open > 0
          ? `${open} to resolve`
          : `${claims.length} claims checked`,
    },
    {
      id: "script",
      label: "Script",
      state: !written ? "todo" : checked ? "done" : "attention",
      note: !written
        ? "Not written"
        : !checked
          ? "Needs checking"
          : flagged > 0
            ? `Checked, ${flagged} flagged`
            : "Checked",
    },
    {
      id: "voice",
      label: "Voice",
      state: voiced ? "done" : "todo",
      note: voiced ? "Voiced" : "Not voiced",
    },
  ];
}

/**
 * Where to put the reader when they open an item: the first step still to do.
 * A draft nobody has checked yet opens on the draft, so it is read before it
 * is checked.
 */
export function firstOpenStep(kind: string, content: Content): StepId {
  const review = reviewOf(content);
  if (!review.facts && !review.script) return "draft";
  return (
    reviewSteps(kind, content).find((step) => step.state !== "done")?.id ?? "voice"
  );
}
