import { HiOutlineArrowRight, HiOutlineCheckCircle, HiOutlineExclamationTriangle, HiOutlineXCircle } from "react-icons/hi2";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui";
import type { SubSection, PlabEvaluationScore } from "./plabTypes";
export const getScoreColor = (score: number) => {
  if (score >= 0.8) return "text-osce-success-text";
  if (score >= 0.6) return "text-osce-warning-text";
  return "text-osce-danger";
};

export const ScoreCard = ({
  title,
  score,
  items,
}: {
  title: string;
  score: number;
  items: SubSection | PlabEvaluationScore;
}) => (
  <B2CPanelCard className="mt-0">
    <B2CPanelCardHeader>
      <span className="min-w-0 flex-1 truncate">{title}</span>
      <span className={`shrink-0 text-osce-body font-semibold ${getScoreColor(score)}`}>
        {score}/1
      </span>
    </B2CPanelCardHeader>
    <B2CPanelCardBody>
    {(items as SubSection).completed?.length > 0 && (
      <div className="mb-3">
        {" "}
        <h4 className="text-osce-body font-semibold text-b2c-text-secondary mb-2">
          {" "}
          Strengths{" "}
        </h4>{" "}
        <div className="flex items-start text-osce-body text-b2c-text-secondary">
          {" "}
          <HiOutlineCheckCircle className="h-4 w-4 text-osce-success-icon mr-2 mt-0.5" />{" "}
          <div>
            {" "}
            {(items as SubSection).completed
              .map(
                (item: string) =>
                  item.charAt(0).toUpperCase() + item.slice(1),
              )
              .join(", ")}{" "}
          </div>{" "}
        </div>{" "}
      </div>
    )}{" "}
    {(items as SubSection).missed?.length > 0 && (
      <div className="mb-3">
        {" "}
        <h4 className="text-osce-body font-semibold text-b2c-text-secondary mb-2">
          {" "}
          Areas for Improvement{" "}
        </h4>{" "}
        <div className="flex items-start text-osce-body text-b2c-text-secondary">
          {" "}
          <HiOutlineXCircle className="h-6 w-6 text-osce-danger mr-2 mt-0.5" />{" "}
          <div>
            {" "}
            {(items as SubSection).missed
              .map(
                (item: string) =>
                  item.charAt(0).toUpperCase() + item.slice(1),
              )
              .join(", ")}{" "}
          </div>{" "}
        </div>{" "}
      </div>
    )}{" "}
    {items.suggested_actions && items.suggested_actions.length > 0 && (
      <div className="mt-4 py-3 lg:p-3 bg-osce-accent-muted rounded-md">
        {" "}
        <div className="flex items-center">
          {" "}
          <HiOutlineArrowRight className="h-4 w-4 text-osce-accent mr-2" />{" "}
          <h4 className="text-osce-body font-medium text-osce-accent-hover">
            {" "}
            Suggested Actions{" "}
          </h4>{" "}
        </div>{" "}
        <ul className="space-y-1">
          {" "}
          {items.suggested_actions &&
            items.suggested_actions.map((action: string, index: number) => (
              <li key={index} className="text-osce-body text-osce-accent">
                {" "}
                • {action}{" "}
              </li>
            ))}{" "}
        </ul>{" "}
      </div>
    )}{" "}
    {items.critical_flags && items.critical_flags.length > 0 && (
      <div className="mt-4 p-3 bg-osce-danger-bg rounded-md">
        {" "}
        <div className="flex items-center">
          {" "}
          <HiOutlineExclamationTriangle className="h-4 w-4 text-osce-danger mr-2" />{" "}
          <h4 className="text-osce-body font-medium text-osce-danger-text">
            {" "}
            Critical Flags{" "}
          </h4>{" "}
        </div>{" "}
        <ul className="space-y-1">
          {" "}
          {items.critical_flags &&
            items.critical_flags.map((flag: string, index: number) => (
              <li key={index} className="text-osce-body text-osce-danger">
                {" "}
                • {flag}{" "}
              </li>
            ))}{" "}
        </ul>{" "}
      </div>
    )}{" "}
    {items.supporting_phrase && (
      <div className="mt-4 p-3 bg-b2c-surface-muted rounded-md">
        {" "}
        <h4 className="text-osce-body font-semibold text-b2c-text-secondary mb-2">
          {" "}
          Quote{" "}
        </h4>{" "}
        <p className="text-osce-body text-b2c-text-secondary italic">
          {" "}
          &ldquo;{Array.isArray(items.supporting_phrase) ? items.supporting_phrase.join("; ") : items.supporting_phrase}&rdquo;{" "}
        </p>{" "}
      </div>
    )}{" "}
    </B2CPanelCardBody>
  </B2CPanelCard>
);
