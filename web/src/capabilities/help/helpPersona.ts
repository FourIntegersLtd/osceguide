/**
 * Athena, the voice tutor, belongs on clinical surfaces: practice, A to Z,
 * slides, podcasts and the debrief. Contact, Notifications, Settings and
 * Community get text Help only: no voice button, no "Discuss with Athena".
 * That is the Help dock. On Community Athena still signs the assistant's
 * written replies under a question (`QuestionDetail`), but never speaks there.
 * The segment after `/app/<workspace>/` decides, so every workspace agrees.
 */
const TEXT_HELP_ONLY = new Set(["messages", "notifications", "inbox", "settings", "discussion"]);

export function athenaVoiceAllowed(pathname: string | null): boolean {
  const segment = /^\/app\/[^/]+\/([^/?#]+)/.exec(pathname ?? "")?.[1];
  return !(segment && TEXT_HELP_ONLY.has(segment));
}

/** Who the Help dock speaks as: Athena where she speaks, plain Help where it is text only. */
export interface HelpPersona {
  name: string;
  /** The jump-to group her row sits under. */
  group: string;
  /** The jump-to row that opens Help with what was typed. */
  askLabel: (text: string) => string;
}

export function helpPersona(voice: boolean): HelpPersona {
  return voice
    ? { name: "Athena", group: "Athena", askLabel: (text) => `Ask Athena about \u201c${text}\u201d` }
    : { name: "Help", group: "Help", askLabel: (text) => `Help with \u201c${text}\u201d` };
}
