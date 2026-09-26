import { IS_PRODUCTION_SITE } from "@/foundation/config/siteUrl";

/** Production's own GA property, the only place this id is written down. */
const PRODUCTION_GA_MEASUREMENT_ID = "G-57RJ52Q20T";

/**
 * Which GA measurement id (if any) this deployment should load.
 *
 * `NEXT_PUBLIC_GA_MEASUREMENT_ID` unset used to mean "use the default"
 * everywhere this code ran — but this code now also runs on staging and on
 * every Vercel preview, and defaulting there would mix a developer's preview
 * clicks into production's real numbers. So the fallback to production's id
 * applies only when this deployment *is* production (from
 * `foundation/config/siteUrl.ts`, which does not use `NODE_ENV` — see that
 * module's comment for why). Setting the variable to an empty string is a
 * deliberate "load nothing", distinct from leaving it unset, so a preview's
 * own env can turn analytics off without also having to know it is a preview.
 *
 * `isProductionSite` is taken as an argument (rather than reading
 * `IS_PRODUCTION_SITE` inside this function) so a test can assert every
 * combination with literal values. This also keeps the logic in a plain
 * `.ts` module rather than the `.tsx` component that uses it, so a test can
 * import it without pulling in React, `next/script` and JSX.
 */
export function resolveGaMeasurementId(
  configured: string | undefined,
  isProductionSite: boolean,
): string | null {
  if (configured === "") {
    return null;
  }
  if (configured) {
    return configured;
  }
  return isProductionSite ? PRODUCTION_GA_MEASUREMENT_ID : null;
}

/** The id, if any, this running deployment should load. Resolved once, at module load. */
export const GA_MEASUREMENT_ID: string | null = resolveGaMeasurementId(
  process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID,
  IS_PRODUCTION_SITE,
);
