import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";
import type { AssistantSurface } from "@/capabilities/surface";

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

export type AssistantSessionType = "help" | "onboarding" | "dashboard" | "demo";

export function startAssistantSession(
  sessionType: AssistantSessionType,
  context: AssistantClientContext,
  signal?: AbortSignal,
  helpOptions?: { voice_help_intent: "faq" | "guide"; screen_ui_guidance: boolean },
): Promise<AssistantSession> {
  return platformRequest<AssistantSession>("/api/v1/assistant/sessions", {
    method: "POST",
    body: { session_type: sessionType, extras: { client: context, ...helpOptions } },
    signal,
  });
}

export function assistantVoiceToken(sessionId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/assistant/sessions/${encodeURIComponent(sessionId)}/voice-token`,
    { method: "POST", signal },
  );
}

export interface HelpCategory {
  id: string;
  slug: string;
  title: string;
  description: string;
  icon_key: string;
  sort_order: number;
  app_types: string[];
  article_count: number;
}

export interface HelpArticleListItem {
  id: string;
  slug: string;
  title: string;
  summary: string;
  app_types: string[];
  category_slug: string;
  category_title?: string | null;
  sort_order: number;
}

export interface HelpArticleDetail extends HelpArticleListItem {
  body_md: string;
  related_slugs: string[];
}

/** Published B2C help content served by the platform API. */
export function fetchHelpCategories(appType: string): Promise<HelpCategory[]> {
  return platformRequest<{ categories: HelpCategory[] }>("/api/v1/help/categories", {
    query: { app_type: appType },
  }).then((data) => data.categories ?? []);
}

export function fetchHelpArticles(
  appType: string,
  categorySlug?: string,
): Promise<HelpArticleListItem[]> {
  return platformRequest<{ articles: HelpArticleListItem[] }>("/api/v1/help/articles", {
    query: {
      app_type: appType,
      ...(categorySlug ? { category: categorySlug } : {}),
    },
  }).then((data) => data.articles ?? []);
}

export function fetchHelpArticle(slug: string, appType: string): Promise<HelpArticleDetail> {
  return platformRequest<{ article: HelpArticleDetail }>(
    `/api/v1/help/articles/${encodeURIComponent(slug)}`,
    { query: { app_type: appType } },
  ).then((data) => data.article);
}

export interface KnowledgeMessage { role: "user" | "assistant"; content: string }
export function askKnowledge(messages: KnowledgeMessage[], appType: string): Promise<{ reply: string }> {
  return platformRequest("/api/v1/help/knowledge-chat", { method: "POST", body: { messages: messages.slice(-40), app_type: appType } });
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
