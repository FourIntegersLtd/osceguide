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
  "export_results",
  // Writing stations, templates, rubrics, exams and programmes: the authoring write routes
  // are OrgAdmin inside an organisation, and the platform admin's on the staff console.
  "author_content",
  "administer_platform",
] as const;

export type Permission = (typeof PERMISSIONS)[number];
