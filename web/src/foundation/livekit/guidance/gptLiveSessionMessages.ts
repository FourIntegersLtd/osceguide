export const DATA_TYPE_GPT_LIVE_SESSION_WARNING = "gpt_live_session_warning";
export const DATA_TYPE_GPT_LIVE_SESSION_ENDED = "gpt_live_session_ended";

export type GptLiveSessionNotice = {
  type: "warning" | "ended";
  message: string;
  reason?: string;
};

export function parseGptLiveSessionMessage(
  payload: Uint8Array,
): GptLiveSessionNotice | null {
  try {
    const raw = JSON.parse(new TextDecoder().decode(payload)) as {
      type?: string;
      message?: string;
      reason?: string;
    };
    if (raw.type === DATA_TYPE_GPT_LIVE_SESSION_WARNING) {
      return {
        type: "warning",
        message: raw.message || "Your voice session will end soon.",
        reason: raw.reason,
      };
    }
    if (raw.type === DATA_TYPE_GPT_LIVE_SESSION_ENDED) {
      const reason = raw.reason || "ended";
      const message =
        reason === "hard_timeout"
          ? "This voice session reached the five-minute limit and has ended."
          : reason === "idle_timeout"
            ? "This voice session ended because there was no response."
            : "This voice session has ended.";
      return { type: "ended", message, reason };
    }
  } catch {
    return null;
  }
  return null;
}
