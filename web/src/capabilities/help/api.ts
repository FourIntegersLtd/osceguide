import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";
import type { AssistantSurface } from "@/capabilities/surface";
import { isMediaKind, type MediaKind } from "@/capabilities/media/api";

export type AssistantSession = components["schemas"]["SessionRead"];

/**
 * What the client tells the backend about where the person is standing.
 *
 * The backend selects a help pack from surface x exam x role and renders the
 * client's own navigation labels into the answers, so the assistant says "open
 * Sittings" on an institution screen and "open Mocks" on a consumer one
 * without either client shipping a script. Mirrors
 * `assistant_content/request.py`; the caps are the backend's.
 */
export interface AssistantClientContext {
  surface: AssistantSurface;
  route: string;
  navigation: { key: string; label: string; path: string }[];
}

export const MAX_ROUTE_CHARS = 200;
export const MAX_NAV_ITEMS = 40;
export const MAX_NAV_FIELD_CHARS = 120;

const clip = (value: string, limit: number) => value.trim().slice(0, limit);

export function buildClientContext(input: {
  surface: AssistantSurface;
  pathname: string | null | undefined;
  navItems?: { key: string; label: string; path: string }[];
}): AssistantClientContext {
  return {
    surface: input.surface,
    route: clip(input.pathname ?? "", MAX_ROUTE_CHARS),
    navigation: (input.navItems ?? [])
      .filter((item) => item.key.trim().length > 0)
      .slice(0, MAX_NAV_ITEMS)
      .map((item) => ({
        key: clip(item.key, MAX_NAV_FIELD_CHARS),
        label: clip(item.label, MAX_NAV_FIELD_CHARS),
        path: clip(item.path, MAX_ROUTE_CHARS),
      })),
  };
}

export type AssistantSessionType = "help" | "onboarding" | "dashboard";

/** One entry of the shell's menu, as Athena is told it: she names pages the way it does. */
export interface HelpNavItem {
  key: string;
  label: string;
  path: string;
}

/**
 * Open Athena from anywhere and start talking. The dock on every signed-in
 * shell listens for this; `onboarding` starts the guided tour instead.
 */
export function openAthena(kind: "athena" | "onboarding" = "athena", topic?: AthenaTopic): void {
  window.dispatchEvent(new CustomEvent("osce:open-athena", { detail: { kind, topic } }));
}

/**
 * What a conversation with Athena is opened on: a question somebody typed, or
 * the thing they were reading. She greets them with it and starts there. The
 * backend caps and validates it (`assistant/content/request.py`, `parse_topic`).
 */
export interface AthenaTopic {
  title: string;
  /** The kind of reading it came from, when it came from one. */
  kind?: MediaKind;
  slug?: string;
}

export interface AthenaLaunch {
  kind: "athena" | "onboarding";
  topic: AthenaTopic | null;
}

/** The `osce:open-athena` event's detail, read without trusting its shape. */
export function readAthenaLaunch(detail: unknown): AthenaLaunch {
  const fields = typeof detail === "object" && detail !== null ? (detail as Record<string, unknown>) : {};
  const kind = fields.kind === "onboarding" ? "onboarding" : "athena";
  const rawTopic =
    typeof fields.topic === "object" && fields.topic !== null ? (fields.topic as Record<string, unknown>) : {};
  const title = typeof rawTopic.title === "string" ? rawTopic.title.trim() : "";
  if (!title) return { kind, topic: null };
  const topic: AthenaTopic = { title };
  if (typeof rawTopic.kind === "string" && isMediaKind(rawTopic.kind)) topic.kind = rawTopic.kind;
  if (typeof rawTopic.slug === "string" && rawTopic.slug.trim()) topic.slug = rawTopic.slug.trim();
  return { kind, topic };
}

export function startAssistantSession(
  sessionType: AssistantSessionType,
  context: AssistantClientContext,
  signal?: AbortSignal,
  helpOptions?: { voice_help_intent: "faq" | "guide"; screen_ui_guidance: boolean },
  topic?: AthenaTopic | null,
): Promise<AssistantSession> {
  return platformRequest<AssistantSession>("/api/v1/assistant/sessions", {
    method: "POST",
    body: { session_type: sessionType, extras: { client: context, ...helpOptions, ...(topic ? { topic } : {}) } },
    signal,
  });
}

export function assistantVoiceToken(sessionId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/assistant/sessions/${encodeURIComponent(sessionId)}/voice-token`,
    { method: "POST", signal },
  );
}

export type HelpCategory = components["schemas"]["HelpCategory"];
export type HelpArticle = components["schemas"]["HelpArticle"];

/**
 * Published help content served by the platform API. With no exam, only the
 * guides written for every exam come back.
 */
export function fetchHelpCategories(examCode?: string): Promise<HelpCategory[]> {
  return platformRequest<{ categories: HelpCategory[] }>("/api/v1/help/categories", {
    query: examCode ? { exam_code: examCode } : {},
  }).then((data) => data.categories ?? []);
}

/** `search` is matched against title, summary and category in SQL. */
export function fetchHelpArticles(
  examCode?: string,
  categorySlug?: string,
  search?: string,
): Promise<HelpArticle[]> {
  return platformRequest<{ articles: HelpArticle[] }>("/api/v1/help/articles", {
    query: {
      ...(examCode ? { exam_code: examCode } : {}),
      ...(categorySlug ? { category: categorySlug } : {}),
      ...(search?.trim() ? { search: search.trim() } : {}),
    },
  }).then((data) => data.articles ?? []);
}

export function fetchHelpArticle(slug: string, examCode?: string): Promise<HelpArticle> {
  return platformRequest<{ article: HelpArticle }>(
    `/api/v1/help/articles/${encodeURIComponent(slug)}`,
    { query: examCode ? { exam_code: examCode } : {} },
  ).then((data) => data.article);
}

export interface KnowledgeMessage { role: "user" | "assistant"; content: string }
export function askKnowledge(messages: KnowledgeMessage[], examCode?: string): Promise<{ reply: string }> {
  return platformRequest("/api/v1/help/knowledge-chat", { method: "POST", body: { messages: messages.slice(-40), exam_code: examCode } });
}

export type SendMessageInput = components["schemas"]["SendMessage"];
export type MessageAccepted = components["schemas"]["MessageAccepted"];

/**
 * Write to the team: a contact message or product feedback.
 *
 * `POST /site/messages` takes both, told apart by `kind` — "contact" or
 * "product_feedback" — and works signed in or out. When there is a token the
 * message is filed against the person, which is how a reply finds them
 * without the form asking for an address again. It replaced the retiring
 * backend's `/api/create_message` and `/api/add_feature`.
 *
 * The backend rate-limits this to five messages per ten minutes per caller;
 * over that it answers `too_many_requests`, which is a message for a human,
 * so surface `error.message` rather than a generic failure.
 */
export function sendSiteMessage(
  body: SendMessageInput,
  signal?: AbortSignal,
): Promise<MessageAccepted> {
  return platformRequest<MessageAccepted>("/api/v1/site/messages", {
    method: "POST",
    body,
    signal,
  });
}
