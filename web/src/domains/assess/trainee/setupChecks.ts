/** What the tech-check page decides from the browser and the network. Pure, so each answer is tested. */

/** The parts of the browser an assessment room needs; read from `window` by the page. */
export type BrowserEnv = {
  secureContext: boolean;
  hasMicrophoneApi: boolean;
  hasWebRtc: boolean;
  hasWebSocket: boolean;
};

export type CheckResult = { ok: boolean; title: string; detail: string };

export function browserEnv(): BrowserEnv {
  const w = typeof window === "undefined" ? null : window;
  return {
    secureContext: w?.isSecureContext ?? false,
    hasMicrophoneApi: typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia),
    hasWebRtc: w !== null && "RTCPeerConnection" in w,
    hasWebSocket: w !== null && "WebSocket" in w,
  };
}

/** Whether this browser can open the room, and if not what to do about it. */
export function browserVerdict(env: BrowserEnv): CheckResult {
  if (!env.secureContext || !env.hasMicrophoneApi) {
    return {
      ok: false,
      title: "This browser cannot use your microphone here",
      detail: "Open this page in a recent version of Chrome, Edge, Safari or Firefox, at its normal https address.",
    };
  }
  if (!env.hasWebRtc || !env.hasWebSocket) {
    return {
      ok: false,
      title: "This browser cannot join a live room",
      detail: "Update your browser or switch to a recent version of Chrome, Edge, Safari or Firefox.",
    };
  }
  return { ok: true, title: "Your browser is supported", detail: "It can open the room and send your voice." };
}

/** A round trip over this long is slow enough to make a live conversation stutter. */
export const SLOW_MS = 1500;

/** The connection, from whether the browser is online and how long one request to us took (null: it failed). */
export function connectionVerdict(online: boolean, roundTripMs: number | null): CheckResult {
  if (!online || roundTripMs === null) {
    return {
      ok: false,
      title: "We could not reach OSCE Guide",
      detail: "Check your internet connection, then test again. A wired or stronger wifi connection helps.",
    };
  }
  if (roundTripMs > SLOW_MS) {
    return {
      ok: false,
      title: "Your connection is slow",
      detail: "Move closer to your router or switch to a wired connection, and close other apps that use the internet.",
    };
  }
  return { ok: true, title: "Your connection is good", detail: `We reached OSCE Guide in ${Math.max(1, Math.round(roundTripMs))} ms.` };
}
