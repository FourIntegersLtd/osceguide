import { HiOutlineCheckCircle, HiOutlineChevronDown, HiOutlineClipboardDocumentList, HiOutlineLightBulb } from "react-icons/hi2";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui";
import type { OrthoEvaluationScore } from "./orthoTypes";
export const ScoreCard = ({
  title,
  score,
  items,
  isExpanded,
  onToggle,
}: {
  title: string;
  score: number;
  description: string;
  items: OrthoEvaluationScore;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  const getScoreColor = (score: number) => {
    if (score >= 9) return "text-osce-success-text bg-osce-success-bg";
    if (score >= 7) return "text-osce-accent bg-osce-accent-muted";
    if (score >= 4) return "text-osce-warning-text bg-osce-warning-bg";
    return "text-osce-danger bg-osce-danger-bg";
  };
  return (
    <B2CPanelCard className="mt-0 !rounded-none">
      <button
        type="button"
        className="w-full text-left"
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        <B2CPanelCardHeader className="cursor-pointer rounded-none hover:bg-b2c-secondary">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-osce-subheading font-bold sm:h-12 sm:w-12 ${getScoreColor(score)}`}
          >
            {score}
          </div>
          <span className="min-w-0 flex-1 truncate sm:whitespace-normal">
            {title}
          </span>
          <HiOutlineChevronDown
            className={`ml-2 h-4 w-4 shrink-0 text-b2c-text-muted transition-transform ${isExpanded ? "rotate-180" : ""}`}
          />
        </B2CPanelCardHeader>
      </button>
      {isExpanded && (
        <B2CPanelCardBody className="space-y-3">
          {" "}
          {/* Score Justification */}{" "}
          {items.score_justification && (
            <div>
              {" "}
              <p className="text-osce-body text-b2c-text-secondary leading-relaxed">
                {items.score_justification}
              </p>{" "}
            </div>
          )}{" "}
          {/* Strengths */}{" "}
          {items.completed && items.completed.length > 0 && (
            <div>
              {" "}
              <h4 className="text-osce-body font-semibold text-b2c-text-secondary mb-2">
                Strengths
              </h4>{" "}
              <ul className="space-y-1.5">
                {" "}
                {items.completed.map((item, index) => (
                  <li
                    key={index}
                    className="flex items-start text-osce-body text-b2c-text-secondary"
                  >
                    {" "}
                    <HiOutlineCheckCircle className="w-4 h-4 text-osce-success-icon mr-2 mt-0.5 flex-shrink-0" />{" "}
                    <span className="flex-1">{item}</span>{" "}
                  </li>
                ))}{" "}
              </ul>{" "}
            </div>
          )}{" "}
          {/* Evidence Points */}{" "}
          {items.evidence_points && items.evidence_points.length > 0 && (
            <div>
              {" "}
              <h4 className="text-osce-body font-semibold text-b2c-text-secondary mb-2 flex items-center">
                {" "}
                <HiOutlineClipboardDocumentList className="mr-1.5 w-4 h-4 flex-shrink-0 text-osce-accent" />{" "}
                Evidence{" "}
              </h4>{" "}
              <ul className="space-y-1.5">
                {" "}
                {items.evidence_points.map((point, index) => (
                  <li
                    key={index}
                    className="text-osce-body text-b2c-text-secondary flex items-start"
                  >
                    {" "}
                    <span className="mr-2 text-b2c-text-muted">•</span>{" "}
                    <span className="flex-1">{point}</span>{" "}
                  </li>
                ))}{" "}
              </ul>{" "}
            </div>
          )}{" "}
          {/* Suggested Actions */}{" "}
          {items.suggested_actions && items.suggested_actions.length > 0 && (
            <div className="pt-2">
              {" "}
              <h4 className="text-osce-body font-semibold text-b2c-text-secondary mb-2 flex items-center">
                {" "}
                <HiOutlineLightBulb className="mr-1.5 w-5 h-5 flex-shrink-0 text-osce-accent" />{" "}
                Action Points{" "}
              </h4>{" "}
              <ul className="space-y-1.5">
                {" "}
                {items.suggested_actions.map((action, index) => (
                  <li
                    key={index}
                    className="text-osce-body text-b2c-text-secondary flex items-start"
                  >
                    {" "}
                    <span className="mr-2 text-b2c-text-muted flex-shrink-0">
                      {index + 1}.
                    </span>{" "}
                    <span className="flex-1">{action}</span>{" "}
                  </li>
                ))}{" "}
              </ul>{" "}
            </div>
          )}{" "}
        </B2CPanelCardBody>
      )}{" "}
    </B2CPanelCard>
  );
};
