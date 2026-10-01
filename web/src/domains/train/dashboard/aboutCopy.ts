import { chartColors } from "@/foundation/charts/chartTheme";
import type { DashboardView } from "@/domains/train/dashboard/dashboardView";
import type { AboutContent, AboutItem, AboutKey, ExamAbout } from "@/domains/train/dashboard/aboutTypes";

/**
 * What the three "about" modals say, written from the dashboard's own view.
 *
 * The retiring client shipped a copy per exam, and the wording drifted from
 * the numbers: SCA's modal described a chart the screen no longer drew. Here
 * the sentences quote the same scale, pass line and labels the charts use, so
 * they cannot disagree, and a new exam's modals are right on day one.
 */

export type { AboutContent, AboutItem, AboutKey, ExamAbout };

const REMEMBER = {
  label: "Remember",
  text: "Every expert was once a beginner. Your performance today is the foundation for tomorrow's success. Focus on progress, not perfection.",
};

/** The competency mix, for an exam counted by grade. */
function mixAbout(): AboutContent {
  return {
    title: "Your competency mix",
    description: "How your assessed marks split across the three levels, across every station you have completed.",
    sectionTitle: "The three levels",
    sectionTone: "sky",
    items: [
      { marker: "success", title: "Competent", description: "Marks at the best grade: the standard expected in the exam." },
      { marker: "plain", title: "Developing", description: "Marks close to the line. These are the quickest to improve." },
      { marker: "danger", title: "Development", description: "Marks at the lowest grade. Practise these areas next." },
    ],
  };
}

/** Pass and fail rates, for an exam with a pass line. */
function ratesAbout(view: DashboardView): AboutContent {
  const passLabel = view.display?.labels.passLabel;
  return {
    title: "Your learning journey",
    description:
      "This section shows your progress across all completed stations. Remember, every station is a learning opportunity on your path to success.",
    sectionTitle: "What the scores mean",
    sectionTone: "sky",
    items: [
      {
        marker: "success",
        title: "Strong performance",
        description: passLabel
          ? `Stations at or above the pass line (${passLabel}). These show where you are exam-ready.`
          : "Stations where you met the pass line. These show where you are exam-ready.",
      },
      {
        marker: "danger",
        title: "Growth opportunities",
        description:
          "Stations with room for development. These are valuable learning experiences that guide your focused preparation.",
      },
    ],
    callout: REMEMBER,
  };
}

function domainAbout(view: DashboardView): AboutContent {
  const chart = view.domainChart;
  if (chart.kind === "counts") {
    return {
      title: "Domain performance",
      description: `${chart.subtitle}. Each bar splits one domain's marks by grade.`,
      sectionTitle: "The three colours",
      sectionTone: "sky",
      items: [
        { marker: "swatch", color: chartColors.green, title: "Competent", description: "Marks at the best grade." },
        { marker: "swatch", color: chartColors.amber, title: "Developing", description: "Marks in between." },
        { marker: "swatch", color: chartColors.red, title: "Requires development", description: "Marks at the lowest grade." },
      ],
      callout: { label: "Note", text: "A good consultation needs every domain. Look at your weakest bar and practise that next." },
    };
  }
  return {
    title: "Domain performance",
    description: `${chart.subtitle}, across every station you have completed.`,
    sectionTitle: "Assessment domains",
    sectionTone: "sky",
    items: chart.bars.map((bar) => ({
      marker: "swatch",
      color: bar.color,
      title: bar.name,
      description: `Your score so far: ${chart.format(bar.score)}.`,
    })),
    callout:
      chart.threshold !== undefined
        ? {
            label: "Note",
            text: `The line at ${chart.format(chart.threshold)} (${chart.thresholdLabel ?? "pass line"}) is the minimum each domain needs.`,
          }
        : undefined,
  };
}

function trendAbout(view: DashboardView): AboutContent {
  const trend = view.trend;
  const items: AboutItem[] = [
    view.counted
      ? { marker: "plain", title: "Competency rate", description: "Each point is one station's share of marks at the best grade." }
      : { marker: "plain", title: "Station scores", description: `Each point is one station's total, out of ${trend.format(trend.maxScore)}.` },
  ];
  if (trend.threshold !== undefined) {
    items.push({
      marker: "threshold",
      title: trend.thresholdLabel ?? "Pass line",
      description: `The line at ${trend.format(trend.threshold)} is the total a station needs to pass.`,
    });
  } else {
    items.push({
      marker: "plain",
      title: "Direction matters",
      description: "A rising line is what to aim for; a single low station is not a verdict.",
    });
  }
  return {
    title: "Performance trend",
    description: trend.subtitle,
    sectionTitle: "How to read the chart",
    sectionTone: "amber",
    items,
    callout: view.bands.length ? { label: "Bands", text: view.bands.join(" · ") } : undefined,
  };
}

export function aboutFor(view: DashboardView): ExamAbout {
  return {
    summary: view.counted ? mixAbout() : ratesAbout(view),
    domain: domainAbout(view),
    trend: trendAbout(view),
  };
}
