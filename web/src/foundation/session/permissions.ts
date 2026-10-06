/**
 * The permissions `/me/capabilities` answers, named once.
 *
 * These strings are the backend's, from `tenancy/service.py`. Keeping them in a
 * union rather than scattering string literals means a renamed permission is a
 * compile error here instead of a screen that silently hides itself — which is
 * how a guard quietly denies everyone.
 */
export const PERMISSIONS = [
  "read_org",
  "manage_team",
  "run_circuits",
  "schedule_sittings",
  "sign_off_results",
  "administer_platform",
] as const;

export type Permission = (typeof PERMISSIONS)[number];
