import type { AttemptReview } from "@/capabilities/attempt-runner/api";

export type InterviewQuestion = { question: string; answer: string };
export type WardPatient = { number: string | number; age: string | number; gender: string; summary: string; notes: string[] };
export type TheatreItem = { title: string; reasons: string[] };
export type Station = Pick<NonNullable<AttemptReview["teaching"]>,
  "key_concerns" | "history_overview" | "examination_overview" | "investigations_overview" |
  "management_overview" | "references" | "suggested_order_overview" | "communication_themes" |
  "consent_approach" | "breaking_bad_news_framework" | "professional_conduct_topics" |
  "key_learning_points" | "portfolio_themes">
  & Pick<NonNullable<AttemptReview["scenario"]>,
  "station_type" | "clinical_scenario" | "radiograph_image_url" | "additional_image_urls" | "background_overview">
  & {
    station_name: string; station_id: string;
    patient_list_for_candidate: WardPatient[]; examiner_additional_info: WardPatient[];
    interview_questions: InterviewQuestion[];
    suggested_order: Record<string, TheatreItem[]>;
  };

const strings = (value: unknown): string[] => Array.isArray(value)
  ? value.filter((item): item is string => typeof item === "string") : [];
function patients(items: NonNullable<AttemptReview["scenario"]>["patient_list_for_candidate"]): WardPatient[] {
  return (items ?? []).map((item) => ({
    number: item.number ?? "", age: item.age ?? "", gender: item.gender ?? "",
    summary: typeof item.summary === "string" ? item.summary : "", notes: strings(item.notes),
  }));
}

export function stationForReview(review: Pick<AttemptReview, "station_title" | "station_id" | "scenario" | "teaching">): Station {
  const order: Record<string, TheatreItem[]> = {};
  for (const [key, value] of Object.entries(review.teaching?.suggested_order ?? {})) {
    if (!Array.isArray(value)) continue;
    order[key] = value.flatMap((item: unknown) => {
      if (!item || typeof item !== "object" || !("title" in item) || typeof item.title !== "string") return [];
      return [{ title: item.title, reasons: strings("reasons" in item ? item.reasons : []) }];
    });
  }
  return {
    ...review.scenario, ...review.teaching,
    station_name: review.station_title, station_id: review.station_id,
    patient_list_for_candidate: patients(review.scenario?.patient_list_for_candidate),
    examiner_additional_info: patients(review.teaching?.examiner_additional_info),
    interview_questions: (review.teaching?.interview_questions ?? []).map((item) => ({
      question: item.question ?? "", answer: item.answer ?? "",
    })),
    suggested_order: order,
  };
}
