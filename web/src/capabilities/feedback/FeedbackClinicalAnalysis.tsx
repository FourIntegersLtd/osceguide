import { HiOutlinePresentationChartLine } from "react-icons/hi2";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui";
import { Dropdown } from "@/foundation/table";
import type { AnalysisSection } from "@/capabilities/feedback/model";

interface Tone {
  dot: string;
  body: string;
  marker: string | null;
  markerClassName: string;
}

const DEFAULT_TONE: Tone = {
  dot: "bg-osce-accent",
  body: "",
  marker: null,
  markerClassName: "",
};

/**
 * Cosmetic only, and the reason it is a lookup rather than a branch: the
 * warning and danger tones carry meaning on the sections that have them —
 * something missed, something unsafe — and a framework whose analysis this map
 * has never seen renders in the neutral tone instead of not rendering.
 */
const TONES: Record<string, Tone> = {
  missed_history: {
    dot: "bg-osce-warning-icon",
    body: "bg-osce-warning-bg/60",
    marker: "→",
    markerClassName: "text-osce-warning-icon",
  },
  missed_examinations: {
    dot: "bg-osce-warning-icon",
    body: "bg-osce-warning-bg/60",
    marker: "→",
    markerClassName: "text-osce-warning-icon",
  },
  key_positives: { dot: "bg-osce-success-icon", body: "bg-osce-success-bg/60", marker: null, markerClassName: "" },
  key_negatives: { dot: "bg-osce-accent", body: "bg-osce-accent-muted/60", marker: null, markerClassName: "" },
  safety_considerations: {
    dot: "bg-osce-danger",
    body: "bg-osce-danger-bg/60",
    marker: "!",
    markerClassName: "text-osce-danger",
  },
};

/**
 * What the consultation covered clinically, as the marker read it.
 *
 * Sits under the grades rather than beside them: this is the evidence, and it
 * is the part a candidate argues with, so it is rendered whole rather than
 * summarised.
 */
export function FeedbackClinicalAnalysis({ sections }: { sections: AnalysisSection[] }) {
  if (sections.length === 0) return null;

  return (
    <Dropdown
      defaultOpen
      title="Clinical Analysis Feedback"
      icon={<HiOutlinePresentationChartLine className="h-5 w-5" />}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        {sections.map((section) => {
          const tone = TONES[section.key] ?? DEFAULT_TONE;
          return (
            <B2CPanelCard key={section.key} className="mt-0">
              <B2CPanelCardHeader>
                <span className={`h-2 w-2 rounded-full ${tone.dot}`} /> {section.label}
              </B2CPanelCardHeader>
              <B2CPanelCardBody className={tone.body}>
                {section.body ? (
                  <p className="text-b2c-text-secondary">{section.body}</p>
                ) : (
                  <ul className="space-y-2">
                    {section.items.map((item, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-b2c-text-secondary"
                      >
                        {tone.marker ? (
                          <span className={tone.markerClassName}>{tone.marker}</span>
                        ) : null}
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </B2CPanelCardBody>
            </B2CPanelCard>
          );
        })}
      </div>
    </Dropdown>
  );
}
