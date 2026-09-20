/** Phase lengths in seconds, aligned with platform-api peer_practice/timers.py */

export function phaseDurations(examCode: string): {
  preparation: number;
  consultation: number;
  debrief: number;
} {
  const code = examCode.toLowerCase();
  switch (code) {
    case "plab":
      return { preparation: 120, consultation: 480, debrief: 900 };
    case "casc":
      return { preparation: 300, consultation: 420, debrief: 900 };
    case "ortho":
      return { preparation: 300, consultation: 600, debrief: 900 };
    case "sca":
    default:
      return { preparation: 180, consultation: 720, debrief: 900 };
  }
}

export function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
