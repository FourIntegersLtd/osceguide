import { createLocalFlag } from "@/foundation/hooks/createLocalPreference";

/**
 * Whether the learner has hidden live marking. On by default: the tick landing mid-consultation
 * is the point of the feature, and nobody discovers a panel that starts switched off.
 */
export const liveCoverageHidden = createLocalFlag("osce_live_coverage_hidden");
