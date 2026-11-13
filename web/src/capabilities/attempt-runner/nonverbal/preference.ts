import { createLocalFlag } from "@/foundation/hooks/createLocalPreference";

/**
 * Whether the candidate has switched live cues off on this device. Cues are on by default once
 * consent is given; this is only the local switch, and the stored consent is the server's.
 */
export const nonverbalOff = createLocalFlag("osce_nonverbal_off");
