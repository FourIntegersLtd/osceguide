import type { Trainee } from "@/domains/assess/api";

/** Why a rostered trainee cannot be picked, said in the row itself. */
export const NOT_YET_JOINED = "Not yet joined: they can be added once they have signed in.";

export interface LatecomerChoice {
  trainee: Trainee;
  /** Null when they can be picked; otherwise the reason they cannot. */
  refusal: string | null;
}

/**
 * Who on the roster can be added to a running circuit.
 *
 * A slot names a *user*, so who is already on the circuit is a set of user ids,
 * not trainee ids. Somebody who has never signed in has no user yet: they are
 * listed with the reason rather than left out, which read as "not on the roster".
 * The ones who can be picked come first.
 */
export function latecomerChoices(
  roster: Trainee[],
  slots: { trainee: { user_id: string | null } }[],
): LatecomerChoice[] {
  const alreadyOn = new Set(slots.map((slot) => slot.trainee.user_id));
  const choices = roster
    .filter((trainee) => !trainee.access_revoked && (trainee.user_id === null || !alreadyOn.has(trainee.user_id)))
    .map((trainee) => ({ trainee, refusal: trainee.user_id === null ? NOT_YET_JOINED : null }));
  return [...choices.filter((choice) => !choice.refusal), ...choices.filter((choice) => choice.refusal)];
}
