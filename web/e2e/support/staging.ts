/**
 * The staging world: no data is created. Every account and organisation is one
 * a person made once and named in a GitHub secret (docs/CORE-JOURNEYS.md):
 *
 *   STAGING_E2E_WEB_URL, STAGING_E2E_API_URL      where staging is
 *   STAGING_E2E_<ROLE>_EMAIL / _PASSWORD          ROLE: ADMIN SUPERVISOR TRAINEE CONSUMER
 *                                                 HIRE_ADMIN HIRE_CANDIDATE PARTNER_ADMIN PLATFORM
 *   STAGING_E2E_ORG_SLUG, _HIRE_SLUG, _PARTNER_SLUG
 *
 * Only specs tagged @staging run here, and those only read.
 */
import { ROLES, type Account, type Role, type World } from "./world";

/** hireAdmin -> HIRE_ADMIN: ROLES is the only list of roles. */
const envName = (role: Role) => role.replace(/([A-Z])/g, "_$1").toUpperCase();

export function stagingWorld(): World {
  const accounts = {} as Record<Role, Account>;
  for (const role of ROLES) {
    const prefix = `STAGING_E2E_${envName(role)}`;
    accounts[role] = { email: process.env[`${prefix}_EMAIL`] ?? "", password: process.env[`${prefix}_PASSWORD`] ?? "", name: role };
  }
  return {
    target: "staging",
    slug: process.env.STAGING_E2E_ORG_SLUG ?? "",
    orgName: "",
    hireSlug: process.env.STAGING_E2E_HIRE_SLUG ?? "",
    partnerSlug: process.env.STAGING_E2E_PARTNER_SLUG ?? "",
    accounts,
    traineeUserId: "",
    programmeId: "",
    stationVersionIds: [],
  };
}
