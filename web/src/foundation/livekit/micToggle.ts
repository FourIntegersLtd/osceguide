/**
 * The microphone toggle's label and the state it switches to. `whose` names
 * the microphone where another voice's controls sit beside it ("Mute me").
 */
export function micToggle(enabled: boolean, whose?: string): { label: string; next: boolean } {
  const verb = enabled ? "Mute" : "Unmute";
  return { label: whose ? `${verb} ${whose}` : verb, next: !enabled };
}
