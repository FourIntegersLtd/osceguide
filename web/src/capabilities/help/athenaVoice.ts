/**
 * Athena, the voice tutor, belongs on clinical surfaces: practice, A to Z,
 * slides, podcasts and the debrief. Contact, Notifications, Settings and
 * Community get text Help only: no voice button, no "Discuss with Athena".
 * The segment after `/app/<workspace>/` decides, so every workspace agrees.
 */
const TEXT_HELP_ONLY = new Set(["messages", "notifications", "inbox", "settings", "discussion"]);

export function athenaVoiceAllowed(pathname: string | null): boolean {
  const segment = /^\/app\/[^/]+\/([^/?#]+)/.exec(pathname ?? "")?.[1];
  return !(segment && TEXT_HELP_ONLY.has(segment));
}

/** The jump-to row that opens Help with what was typed. */
export function askHelpRow(voice: boolean, text: string): { group: string; label: string } {
  return voice
    ? { group: "Athena", label: `Ask Athena about \u201c${text}\u201d` }
    : { group: "Help", label: `Help with \u201c${text}\u201d` };
}

/** What the dock calls itself: Athena where she speaks, Help where it is text only. */
export function helpPersonaName(voice: boolean): string {
  return voice ? "Athena" : "Help";
}
