// ── Contracts (shared constants & schemas) ───────────────────────────────────
export {
  RPC_METHOD_SCREENSHOT_CHUNKED,
  RPC_METHOD_PERFORM_CLICK,
  RPC_METHOD_SCROLL,
  DATA_TYPE_SCREENSHOT_CHUNK,
  DATA_TYPE_NAV_MODE_CHOICE,
  DATA_TYPE_NAV_MODE_PROMPT,
  POINTER_MESSAGE_TYPE,
  DATA_TYPE_GUIDANCE_PROGRESS,
  TOOL_RUNNING_MESSAGE_TYPE,
  UI_GUIDANCE_SCHEMA_VERSION,
  PROGRESS_STEP_CAPTURING,
  PROGRESS_STEP_READING,
  PROGRESS_STEP_ACTING,
  PROGRESS_STEP_DONE,
  screenshotChunkedRpcRequestSchema,
  screenshotChunkedRpcResponseSchema,
  screenshotChunkDataSchema,
  pointerDataPayloadSchema,
  parsePointerPayload,
  guidanceProgressPayloadSchema,
  parseGuidanceProgressPayload,
  parseKnownAssistantCard,
  performClickRpcRequestSchema,
  performClickRpcResponseSchema,
  performScrollRpcRequestSchema,
  performScrollRpcResponseSchema,
  navModeChoicePayloadSchema,
  navModePromptPayloadSchema,
} from "./contracts";
export type {
  PointerDataPayload,
  PerformClickRpcResponse,
  GuidanceProgressPayload,
  GuidanceProgressStep,
  KnownAssistantCard,
} from "./contracts";
// ── Config ───────────────────────────────────────────────────────────────────
export { isUiGuidanceEnabled } from "./config";
export {
  UI_GUIDANCE_MIN_WIDTH_PX,
  getScreenUiGuidanceActive,
  useScreenUiGuidance,
} from "./screenUiGuidance";
// ── Frontend integration ─────────────────────────────────────────────────────
export { registerScreenshotRpc } from "./registerScreenshotRpc";
export type { RegisterScreenshotRpcOptions } from "./registerScreenshotRpc";
export { registerPerformClickRpc } from "./registerPerformClickRpc";
export { registerScrollRpc } from "./registerScrollRpc";
export { useUiGuidance } from "./useUiGuidance";
export type {
  UiGuidancePointer,
  PointerTarget,
  UseUiGuidanceOptions,
} from "./useUiGuidance";
export { UiGuidanceOverlay } from "./UiGuidanceOverlay";
export { GuidanceProgressPanel } from "./GuidanceProgressPanel";
export { AssistantCards, AssistantCardSlot } from "./AssistantCards";
export type { CardLink, CardLinkFor } from "./AssistantCards";
export type { CardRef } from "./contracts";
export {
  UI_GUIDANCE_IGNORE_ATTRIBUTE,
  uiGuidanceIgnoreProps,
  ignoreMarkedElements,
} from "./captureExclusion";
// ── GPT-Live session notices ─────────────────────────────────────────────────
export {
  DATA_TYPE_GPT_LIVE_SESSION_ENDED,
  DATA_TYPE_GPT_LIVE_SESSION_WARNING,
  parseGptLiveSessionMessage,
} from "./gptLiveSessionMessages";
export type { GptLiveSessionNotice } from "./gptLiveSessionMessages";
