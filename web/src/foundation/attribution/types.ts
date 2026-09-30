/** Who is looking: staff see money, a partner never does. */
export type AttributionMode = "internal" | "partner";

export type RevenueTimeBucket = "day" | "week" | "month";

/** The partner slugs the pilot accepts, mirroring the backend's allowlist. */
export const PILOT_PARTNERS = ["bmj"] as const;

export const PILOT_EXAMS = ["sca", "plab", "ortho"] as const;

/** The filters every dashboard query carries, as the URL holds them. */
export interface AttributionFilters {
  fromDate: string;
  toDate: string;
  partner: string;
  exam: string;
  utmCampaign: string;
}

/** The query parameters the growth routes accept. Empty filters are left off. */
export interface AttributionQuery {
  from_date: string;
  to_date: string;
  exam_code?: string;
  utm_campaign?: string;
}
