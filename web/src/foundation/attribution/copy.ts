import type { AttributionMode, RevenueTimeBucket } from "@/foundation/attribution/types";

/** Seconds-free lifetime of the first-touch acquisition cookie, in days (mirrors the backend). */
export const ACQUISITION_COOKIE_MAX_AGE_DAYS = 90;


export type MethodologyDefinition = {
  term: string;
  detail: string;
  internalOnly?: boolean;
};

export type DashboardCopy = {
  hero: {
    sectionLabel: string;
    title: string;
    hint: string;
    emptyTitle: string;
    emptyDetail: string;
    noBreakdown: string;
    metrics: {
      linkVisits: { label: string; tooltip: string };
      uniquePeople: { label: string; tooltip: string };
      signups: { label: string; tooltip: string };
      paid: { label: string; tooltip: string };
      revenue: { label: string; tooltip: string };
      estimatedFee: { label: string; tooltip: string };
    };
    conversion: {
      signupRate: { label: string; tooltip: string };
      paidRate: { label: string; tooltip: string };
      repeatVisits: { label: string; tooltip: string };
    };
    spend: {
      estimatedSpend: { label: string; tooltip: string };
      moneyLeftOver: { label: string; tooltip: string };
      spendPerSignup: { label: string; tooltip: string };
    };
  };
  funnel: {
    title: string;
    subtitle: string;
    emptyMessage: string;
    emptyHint: string;
  };
  revenueOverTime: {
    title: string;
    subtitleByBucket: Record<RevenueTimeBucket, string>;
    defaultSubtitle: string;
    emptyNoDataMessage: string;
    emptyNoDataHint: string;
    emptyNoPaymentsMessage: string;
    emptyNoPaymentsHint: string;
  };
  revenueByPlan: {
    title: string;
    subtitle: string;
    emptyMessage: string;
    emptyHint: string;
  };
  methodology: {
    introTitle: string;
    introBody: string;
    definitionsHeading: string;
    rulesHeading: string;
    definitions: MethodologyDefinition[];
    rules: MethodologyDefinition[];
  };
  tables: {
    arrivalsDescription: string;
    acquiredUsersDescription: string;
  };
  internalCharts: {
    costVsRevenueSubtitle: string;
  };
  performance: {
    visitsOverTime: {
      title: string;
      subtitle: string;
      emptyMessage: string;
      emptyHint: string;
    };
    signupsOverTime: {
      title: string;
      subtitle: string;
      emptyMessage: string;
      emptyHint: string;
    };
    byExam: {
      title: string;
      description: string;
      dimensionHeader: string;
    };
    byCampaign: {
      title: string;
      description: string;
      dimensionHeader: string;
    };
  };
  feeOverTime: {
    title: string;
    subtitleByBucket: Record<RevenueTimeBucket, string>;
    defaultSubtitle: string;
    emptyMessage: string;
    emptyHint: string;
  };
};

const PARTNER_COPY: DashboardCopy = {
  hero: {
    sectionLabel: "Overview",
    title: "How your links are performing",
    hint: "Visits, sign-ups, and your estimated fee for this period.",
    emptyTitle: "No activity yet",
    emptyDetail: "When people open your links, the numbers will show up here.",
    noBreakdown: "No breakdown yet",
    metrics: {
      linkVisits: {
        label: "Link visits",
        tooltip: "How many times someone opened a page with your link.",
      },
      uniquePeople: {
        label: "Unique people",
        tooltip:
          "How many different people visited. One person can open your link more than once.",
      },
      signups: {
        label: "Sign-ups",
        tooltip: "New accounts where we recorded you as the source they came from.",
      },
      paid: {
        label: "Paid",
        tooltip:
          "People who signed up through your link and paid for a subscription in the dates you selected.",
      },
      revenue: {
        label: "Revenue",
        tooltip: "Not shown on the partner dashboard.",
      },
      estimatedFee: {
        label: "Estimated fee",
        tooltip:
          "A rough guide: your link visits in this period times our agreed rate per visit. You invoice from your own records.",
      },
    },
    conversion: {
      signupRate: {
        label: "Sign-up rate",
        tooltip: "What share of link visits led to a new account.",
      },
      paidRate: {
        label: "Paid rate",
        tooltip: "What share of sign-ups went on to pay in the dates you selected.",
      },
      repeatVisits: {
        label: "Repeat visits",
        tooltip:
          "Extra link opens beyond the first visit per person. One person can open your link more than once.",
      },
    },
    spend: {
      estimatedSpend: {
        label: "Est. BMJ spend",
        tooltip:
          "A rough guess based on link visits and our agreed rate per visit. BMJ invoices from their own records.",
      },
      moneyLeftOver: {
        label: "Money left over",
        tooltip:
          "Subscription money minus estimated BMJ spend. Negative means spend may be higher than revenue.",
      },
      spendPerSignup: {
        label: "Spend per sign-up",
        tooltip:
          "Estimated BMJ spend divided by sign-ups — what each new sign-up cost on average.",
      },
    },
  },
  funnel: {
    title: "From visit to payment",
    subtitle: "How many people reached each step",
    emptyMessage: "Nothing to show for these dates",
    emptyHint: "Try widening the date range or removing filters.",
  },
  revenueOverTime: {
    title: "Revenue over time",
    subtitleByBucket: {
      day: "Daily money from people who came through your links",
      week: "Weekly money from people who came through your links",
      month: "Monthly money from people who came through your links",
    },
    defaultSubtitle: "Money from people who came through your links",
    emptyNoDataMessage: "No money in this date range",
    emptyNoDataHint: "Payments show up when people from your links buy a plan.",
    emptyNoPaymentsMessage: "No payments in this date range",
    emptyNoPaymentsHint: "Try a wider date range or check your filters.",
  },
  revenueByPlan: {
    title: "Money by plan",
    subtitle: "How much people spent on each subscription plan",
    emptyMessage: "No payments in this date range",
    emptyHint: "Payments show up when people from your links buy a plan.",
  },
  methodology: {
    introTitle: "How we count your results",
    introBody:
      "These are the rules behind the numbers you see here. If something looks wrong, tell us the dates you were viewing and what seemed off.",
    definitionsHeading: "What the numbers mean",
    rulesHeading: "How we decide who gets credit",
    definitions: [
      {
        term: "Link visit",
        detail: "Someone clicked your link and opened a page on OSCE Guide.",
      },
      {
        term: "Unique people",
        detail:
          "How many different people visited. The same person can open your link more than once.",
      },
      {
        term: "Sign-up",
        detail: "Someone created an OSCE Guide account after coming from your link.",
      },
      {
        term: "Paid",
        detail:
          "Someone who signed up through your link and paid for a subscription in the dates you selected.",
      },
      {
        term: "Estimated fee",
        detail:
          "Link visits in the date range times our agreed rate per visit (pilot default £0.40). This is a guide only — you invoice from your own click records.",
      },
      {
        term: "Est. BMJ spend",
        detail:
          "A rough guess: link visits in the date range times our agreed rate per visit (pilot default £0.40). BMJ bills from their own records, not this number.",
        internalOnly: true,
      },
      {
        term: "Money left over",
        detail:
          "Subscription money from people who came through your links, minus our estimated BMJ spend. Negative means spend may be higher than revenue in that period.",
        internalOnly: true,
      },
      {
        term: "Spend per sign-up",
        detail:
          "Estimated BMJ spend divided by sign-ups — what we think each new sign-up cost on average.",
        internalOnly: true,
      },
    ],
    rules: [
      {
        term: "Which link gets credit",
        detail:
          "We credit the first partner link someone clicks. If they are already linked to a partner, a later link will not replace it.",
      },
      {
        term: "How long we remember a visit",
        detail: `A sign-up can be linked to your visit for up to ${ACQUISITION_COOKIE_MAX_AGE_DAYS} days after they clicked.`,
      },
      {
        term: "Date range",
        detail:
          "Visits and your estimated fee use when people clicked. Sign-ups use when they registered. Paid uses when they subscribed.",
      },
      {
        term: "Filters",
        detail:
          "Choosing an exam or campaign updates every number on the dashboard to match.",
      },
    ],
  },
  tables: {
    arrivalsDescription: "People who opened one of your links.",
    acquiredUsersDescription: "Accounts created after someone clicked your link.",
  },
  internalCharts: {
    costVsRevenueSubtitle:
      "Estimated BMJ spend compared with subscription money from your links",
  },
  performance: {
    visitsOverTime: {
      title: "Link visits over time",
      subtitle: "How many times people opened your links",
      emptyMessage: "No link visits in this date range",
      emptyHint: "Try widening the date range or removing filters.",
    },
    signupsOverTime: {
      title: "Sign-ups over time",
      subtitle: "New accounts from your links",
      emptyMessage: "No sign-ups in this date range",
      emptyHint: "Try widening the date range or removing filters.",
    },
    byExam: {
      title: "By exam",
      description: "How link visits split across SCA, PLAB, and Ortho.",
      dimensionHeader: "Exam",
    },
    byCampaign: {
      title: "By campaign",
      description: "Which campaigns drove the most activity (top 10).",
      dimensionHeader: "Campaign",
    },
  },
  feeOverTime: {
    title: "Estimated fee over time",
    subtitleByBucket: {
      day: "Daily estimated fee from your link visits",
      week: "Weekly estimated fee from your link visits",
      month: "Monthly estimated fee from your link visits",
    },
    defaultSubtitle: "Estimated fee from your link visits",
    emptyMessage: "No link visits in this date range",
    emptyHint: "Your estimated fee appears when people open your links.",
  },
};

const INTERNAL_COPY: DashboardCopy = {
  hero: {
    sectionLabel: "Overview",
    title: "How partner links are performing",
    hint: "Hover a card to see what each number means.",
    emptyTitle: "No activity yet",
    emptyDetail:
      "When people open partner links, the numbers will show up here.",
    noBreakdown: "No breakdown yet",
    metrics: {
      linkVisits: {
        label: "Link visits",
        tooltip: "How many times someone opened a page with a partner link.",
      },
      uniquePeople: {
        label: "Unique people",
        tooltip:
          "How many different people visited. One person can open a partner link more than once.",
      },
      signups: {
        label: "Sign-ups",
        tooltip:
          "New accounts attributed to a partner link in the selected date range.",
      },
      paid: {
        label: "Paid",
        tooltip:
          "People who signed up through a partner link and paid for a subscription in the selected date range.",
      },
      revenue: {
        label: "Revenue",
        tooltip:
          "Total subscription money from partner-referred users in this period, before refunds.",
      },
      estimatedFee: {
        label: "Estimated fee",
        tooltip: "Not shown on the internal dashboard.",
      },
    },
    conversion: {
      signupRate: { label: "Sign-up rate", tooltip: "" },
      paidRate: { label: "Paid rate", tooltip: "" },
      repeatVisits: { label: "Repeat visits", tooltip: "" },
    },
    spend: {
      estimatedSpend: {
        label: "Est. BMJ spend",
        tooltip:
          "A rough guess based on link visits and our agreed rate per visit. BMJ invoices from their own records.",
      },
      moneyLeftOver: {
        label: "Money left over",
        tooltip:
          "Subscription money minus estimated BMJ spend. Negative means spend may be higher than revenue.",
      },
      spendPerSignup: {
        label: "Spend per sign-up",
        tooltip:
          "Estimated BMJ spend divided by sign-ups — what each new sign-up cost on average.",
      },
    },
  },
  funnel: {
    title: "From visit to payment",
    subtitle: "How many people reached each step",
    emptyMessage: "Nothing to show for these dates",
    emptyHint: "Try widening the date range or adjusting filters.",
  },
  revenueOverTime: {
    title: "Revenue over time",
    subtitleByBucket: {
      day: "Daily subscription revenue from partner-referred users",
      week: "Weekly subscription revenue from partner-referred users",
      month: "Monthly subscription revenue from partner-referred users",
    },
    defaultSubtitle: "Subscription revenue from partner-referred users",
    emptyNoDataMessage: "No revenue in this date range",
    emptyNoDataHint:
      "Payments show up when partner-referred users buy a plan.",
    emptyNoPaymentsMessage: "No payments in this date range",
    emptyNoPaymentsHint: "Try a wider date range or adjust filters.",
  },
  revenueByPlan: {
    title: "Money by plan",
    subtitle: "How much partner-referred users spent on each subscription plan",
    emptyMessage: "No payments in this date range",
    emptyHint: "Payments show up when partner-referred users buy a plan.",
  },
  methodology: {
    introTitle: "How we count partner results",
    introBody:
      "These are the rules behind the numbers on this dashboard. If something looks wrong, share the date range and what seemed off.",
    definitionsHeading: "What the numbers mean",
    rulesHeading: "How we decide who gets credit",
    definitions: [
      {
        term: "Link visit",
        detail: "Someone clicked a partner link and opened a page on OSCE Guide.",
      },
      {
        term: "Unique people",
        detail:
          "How many different people visited. The same person can open a partner link more than once.",
      },
      {
        term: "Sign-up",
        detail:
          "Someone created an OSCE Guide account after coming from a partner link.",
      },
      {
        term: "Paid",
        detail:
          "Someone who signed up through a partner link and paid for a subscription in the selected date range.",
      },
      {
        term: "Revenue",
        detail:
          "Total subscription money from those paying users in this period. Refunds are not taken off here.",
      },
      {
        term: "Est. BMJ spend",
        detail:
          "A rough guess: link visits in the date range times our agreed rate per visit (pilot default £0.40). BMJ bills from their own records, not this number.",
        internalOnly: true,
      },
      {
        term: "Money left over",
        detail:
          "Subscription money from partner-referred users, minus our estimated BMJ spend. Negative means spend may be higher than revenue in that period.",
        internalOnly: true,
      },
      {
        term: "Spend per sign-up",
        detail:
          "Estimated BMJ spend divided by sign-ups — what we think each new sign-up cost on average.",
        internalOnly: true,
      },
    ],
    rules: [
      {
        term: "Which link gets credit",
        detail:
          "We credit the first partner link someone clicks. If they are already linked to a partner, a later link will not replace it.",
      },
      {
        term: "How long we remember a visit",
        detail: `A sign-up can be linked to a partner visit for up to ${ACQUISITION_COOKIE_MAX_AGE_DAYS} days after they clicked.`,
      },
      {
        term: "Date range",
        detail:
          "Visits and sign-ups use when they happened. Revenue uses when someone paid. All dates are calendar dates.",
      },
      {
        term: "Filters",
        detail:
          "Choosing an exam or campaign updates every number on the dashboard to match.",
      },
    ],
  },
  tables: {
    arrivalsDescription: "People who opened a partner link.",
    acquiredUsersDescription:
      "Accounts created after someone clicked a partner link.",
  },
  internalCharts: {
    costVsRevenueSubtitle:
      "Estimated BMJ spend compared with subscription money from partner links",
  },
  performance: {
    visitsOverTime: {
      title: "Link visits over time",
      subtitle: "",
      emptyMessage: "",
      emptyHint: "",
    },
    signupsOverTime: {
      title: "Sign-ups over time",
      subtitle: "",
      emptyMessage: "",
      emptyHint: "",
    },
    byExam: {
      title: "By exam",
      description: "",
      dimensionHeader: "Exam",
    },
    byCampaign: {
      title: "By campaign",
      description: "",
      dimensionHeader: "Campaign",
    },
  },
  feeOverTime: {
    title: "Estimated fee over time",
    subtitleByBucket: { day: "", week: "", month: "" },
    defaultSubtitle: "",
    emptyMessage: "",
    emptyHint: "",
  },
};

export function getDashboardCopy(
  mode: AttributionMode,
): DashboardCopy {
  return mode === "partner" ? PARTNER_COPY : INTERNAL_COPY;
}

/** Collect all user-facing strings for copy audits and tests. */
export function flattenDashboardCopy(copy: DashboardCopy): string[] {
  const parts: string[] = [
    copy.hero.title,
    copy.hero.hint,
    copy.hero.emptyDetail,
    ...Object.values(copy.hero.metrics).flatMap((m) => [m.label, m.tooltip]),
    ...Object.values(copy.hero.conversion).flatMap((m) => [m.label, m.tooltip]),
    ...Object.values(copy.hero.spend).flatMap((m) => [m.label, m.tooltip]),
    copy.funnel.emptyHint,
    copy.revenueOverTime.defaultSubtitle,
    copy.revenueOverTime.emptyNoDataHint,
    copy.revenueByPlan.emptyHint,
    copy.methodology.introTitle,
    copy.methodology.introBody,
    ...copy.methodology.definitions.map((d) => d.detail),
    ...copy.methodology.rules.map((r) => r.detail),
    copy.tables.arrivalsDescription,
    copy.tables.acquiredUsersDescription,
    copy.internalCharts.costVsRevenueSubtitle,
  ];
  return parts;
}
