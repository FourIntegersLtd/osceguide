import { z } from "zod";

/**
 * The wire contract between the browser and the LiveKit assistant worker.
 * Mirrored in `assessment/packages/livekit_assistant_worker/ui_guidance/contracts.py`;
 * `test_ui_guidance_contract_drift.py` fails when the two disagree.
 */

// ── RPC method names (worker → browser) ─────────────────────────────────────

/** Trigger a screenshot. Responds with metadata only; pixels arrive as sc_chunk messages. */
export const RPC_METHOD_SCREENSHOT_CHUNKED = "getScreenshotForGuidanceV2" as const;

/** Synthesize a click at viewport CSS pixels. */
export const RPC_METHOD_PERFORM_CLICK = "performUiGuidanceClick" as const;

/** Scroll the main viewport or a nested overflow container. */
export const RPC_METHOD_SCROLL = "performUiGuidanceScroll" as const;

// ── Data-channel message types ──────────────────────────────────────────────

/** Browser → worker: one base64 fragment of a screenshot. */
export const DATA_TYPE_SCREENSHOT_CHUNK = "sc_chunk" as const;

/** Browser → worker: the user picked guided highlights or hands-off navigation. */
export const DATA_TYPE_NAV_MODE_CHOICE = "nav_mode_choice" as const;

/** Worker → browser: emphasize the navigation mode choice. */
export const DATA_TYPE_NAV_MODE_PROMPT = "nav_mode_prompt" as const;

/** Worker → browser: place or clear the pointer overlay. */
export const POINTER_MESSAGE_TYPE = "pointer" as const;

/**
 * Worker → browser: which step of a guidance turn is running.
 * This is the only feedback that spans the model reading the screenshot, because
 * the tool that took it has already returned by then.
 */
export const DATA_TYPE_GUIDANCE_PROGRESS = "guidance_progress" as const;

/**
 * Worker → browser: a card the backend asked to show alongside a tool answer
 * (a suggestion to open, a list of sources). The worker passes it through unchanged.
 */
export const DATA_TYPE_ASSISTANT_CARD = "assistant_card" as const;

/** Superseded by DATA_TYPE_GUIDANCE_PROGRESS; still sent for one release. */
export const TOOL_RUNNING_MESSAGE_TYPE = "tool_running" as const;

/** Increment when a payload on this channel changes in a breaking way. */
export const UI_GUIDANCE_SCHEMA_VERSION = 2;

// ── Screenshot (chunked protocol) ───────────────────────────────────────────

/** The worker sends an id so it can match chunks that arrive before the RPC returns. */
export const screenshotChunkedRpcRequestSchema = z.object({
  screenshotId: z.string(),
});

/**
 * Metadata only. `captureWidth`/`captureHeight` are the real pixel dimensions of
 * the JPEG sent, which is how the worker maps the model's coordinates back to CSS pixels.
 */
export const screenshotChunkedRpcResponseSchema = z.object({
  totalChunks: z.number().positive(),
  viewportWidth: z.number().positive(),
  viewportHeight: z.number().positive(),
  captureWidth: z.number().positive(),
  captureHeight: z.number().positive(),
  mediaType: z.string().optional(),
});

/** Wire keys are short to keep each chunk small. */
export const screenshotChunkDataSchema = z.object({
  type: z.literal(DATA_TYPE_SCREENSHOT_CHUNK),
  /** Same as the RPC request's `screenshotId`. */
  id: z.string(),
  /** Zero-based chunk index; reassemble in order. */
  i: z.number().int().nonnegative(),
  /** Total chunk count for this screenshot. */
  n: z.number().int().positive(),
  /** Base64 substring for this chunk. */
  d: z.string(),
});

// ── Pointer overlay ─────────────────────────────────────────────────────────

export const pointerDataPayloadSchema = z.object({
  type: z.literal(POINTER_MESSAGE_TYPE),
  schemaVersion: z.number().optional(),
  x: z.number(),
  y: z.number(),
  text: z.string().optional(),
  clear: z.boolean().optional(),
});
export type PointerDataPayload = z.infer<typeof pointerDataPayloadSchema>;

export function parsePointerPayload(raw: unknown): PointerDataPayload | null {
  const parsed = pointerDataPayloadSchema.safeParse(raw);
  return parsed.success ? parsed.data : null;
}

// ── Guidance progress ───────────────────────────────────────────────────────

/** The steps a guidance turn moves through, in order. `done` clears the panel. */
export const PROGRESS_STEP_CAPTURING = "capturing" as const;
export const PROGRESS_STEP_READING = "reading" as const;
export const PROGRESS_STEP_ACTING = "acting" as const;
export const PROGRESS_STEP_DONE = "done" as const;

export const guidanceProgressPayloadSchema = z.object({
  type: z.literal(DATA_TYPE_GUIDANCE_PROGRESS),
  schemaVersion: z.number().optional(),
  step: z.enum([
    PROGRESS_STEP_CAPTURING,
    PROGRESS_STEP_READING,
    PROGRESS_STEP_ACTING,
    PROGRESS_STEP_DONE,
  ]),
  /** What the worker is acting on, when it knows. */
  label: z.string().optional(),
});
export type GuidanceProgressPayload = z.infer<typeof guidanceProgressPayloadSchema>;
export type GuidanceProgressStep = GuidanceProgressPayload["step"];

export function parseGuidanceProgressPayload(raw: unknown): GuidanceProgressPayload | null {
  const parsed = guidanceProgressPayloadSchema.safeParse(raw);
  return parsed.success ? parsed.data : null;
}

// ── Perform click (RPC) ─────────────────────────────────────────────────────

export const performClickRpcRequestSchema = z.object({
  x: z.number(),
  y: z.number(),
});
export const performClickRpcResponseSchema = z.object({
  ok: z.boolean(),
  error: z.string().optional(),
  pathname: z.string().optional(),
});
export type PerformClickRpcResponse = z.infer<typeof performClickRpcResponseSchema>;

// ── Scroll (RPC) ────────────────────────────────────────────────────────────

export const performScrollRpcRequestSchema = z.object({
  direction: z.enum(["up", "down", "left", "right"]),
  /** Optional distance in CSS pixels; the browser defaults if omitted. */
  amount_px: z.number().positive().max(2000).optional(),
});
export const performScrollRpcResponseSchema = z.object({
  ok: z.boolean(),
  error: z.string().optional(),
  /** True if the window or a nested container actually moved. */
  moved: z.boolean().optional(),
  scroll_x: z.number().optional(),
  scroll_y: z.number().optional(),
});

// ── Assistant cards (data channel) ──────────────────────────────────────────

/** Only the envelope is fixed here; each `card` kind carries its own fields. */
export const assistantCardPayloadSchema = z
  .object({
    type: z.literal(DATA_TYPE_ASSISTANT_CARD),
    schemaVersion: z.number().optional(),
    card: z.string(),
  })
  .passthrough();
export type AssistantCardPayload = z.infer<typeof assistantCardPayloadSchema>;

export function parseAssistantCardPayload(raw: unknown): AssistantCardPayload | null {
  const parsed = assistantCardPayloadSchema.safeParse(raw);
  return parsed.success ? parsed.data : null;
}

const cardRefSchema = z
  .object({
    kind: z.string(),
    id: z.string(),
    slug: z.string().nullable().optional(),
  })
  .passthrough();

const suggestionCardSchema = z.object({
  type: z.literal(DATA_TYPE_ASSISTANT_CARD),
  card: z.literal("suggestion"),
  title: z.string().min(1),
  reason: z.string().optional(),
  ref: cardRefSchema.optional(),
});

const citationItemSchema = z.object({
  n: z.number().optional(),
  title: z.string().min(1),
  section: z.string().nullable().optional(),
  ref: cardRefSchema.optional(),
});

const citationsCardSchema = z.object({
  type: z.literal(DATA_TYPE_ASSISTANT_CARD),
  card: z.literal("citations"),
  citations: z.array(citationItemSchema).min(1),
});

export type SuggestionCard = z.infer<typeof suggestionCardSchema>;
export type CitationsCard = z.infer<typeof citationsCardSchema>;
export type KnownAssistantCard = SuggestionCard | CitationsCard;

/**
 * A card the screen knows how to draw.
 *
 * Anything else — a future kind, a suggestion with no title — is ignored
 * rather than thrown, so one bad packet cannot take down the voice session.
 */
export function parseKnownAssistantCard(raw: unknown): KnownAssistantCard | null {
  const suggestion = suggestionCardSchema.safeParse(raw);
  if (suggestion.success) return suggestion.data;
  const citations = citationsCardSchema.safeParse(raw);
  if (citations.success) return citations.data;
  return null;
}

// ── Navigation mode (data channel) ──────────────────────────────────────────

export const navModeChoicePayloadSchema = z.object({
  type: z.literal(DATA_TYPE_NAV_MODE_CHOICE),
  schemaVersion: z.number().optional(),
  mode: z.enum(["guide", "automate"]),
});
export const navModePromptPayloadSchema = z.object({
  type: z.literal(DATA_TYPE_NAV_MODE_PROMPT),
  schemaVersion: z.number().optional(),
  requestId: z.string().optional(),
});
