import { createLandingType } from "@/domains/marketing/landingTypography";
import {
  getLandingTheme,
  landingAccent,
} from "@/domains/marketing/landingTheme";

/** Classic B2C marketing tokens — same sky canvas as `/`. */
export const institutionsLandingType = createLandingType("classic");
export const institutionsLandingTheme = getLandingTheme("classic");
export const institutionsLandingAccent = landingAccent;

export const institutionsSectionMuted =
  "border-y border-landing-divider bg-landing-card-muted";
