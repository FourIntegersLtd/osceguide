import { HiOutlineArrowRight, HiOutlineCheckCircle, HiOutlineXCircle } from "react-icons/hi2";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui";
import type { DomainFeedback } from "./cascTypes";
export const FeedbackSection = ({
  feedback,
}: {
  feedback: DomainFeedback;
  domain: string;
}) => {
  return (
    <div className="space-y-6">
      {" "}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>
            <HiOutlineCheckCircle className="text-osce-success-icon" /> Strengths
          </B2CPanelCardHeader>
          <B2CPanelCardBody>
          <ul className="space-y-3">
            {" "}
            {feedback.strengths.map((item, index) => (
              <li key={index} className="border-b border-b2c-border pb-2 last:border-b-0">
                {" "}
                <p className="font-medium">{item.strength}</p>{" "}
                <p className="text-b2c-text-secondary text-osce-body mt-1">
                  {item.example}
                </p>{" "}
              </li>
            ))}{" "}
          </ul>{" "}
          </B2CPanelCardBody>
        </B2CPanelCard>
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>
            <HiOutlineXCircle className="text-osce-danger" /> Areas Requiring
            Improvement
          </B2CPanelCardHeader>
          <B2CPanelCardBody>
          <ul className="space-y-3">
            {" "}
            {feedback.improvements.map((item, index) => (
              <li key={index} className="border-b border-b2c-border pb-2 last:border-b-0">
                {" "}
                <p className="font-medium text-osce-danger">
                  {item.improvement}
                </p>{" "}
                <p className="text-b2c-text-secondary text-osce-body mt-1">
                  {" "}
                  Issue: {item.issue}{" "}
                </p>{" "}
              </li>
            ))}{" "}
          </ul>{" "}
          </B2CPanelCardBody>
        </B2CPanelCard>
      </div>{" "}
      {/* Detailed Improvement Guide */}{" "}
      {feedback.suggested_actions.length > 0 && (
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>
            <HiOutlineArrowRight className="text-osce-accent" /> Specific Actions
            for Improvement
          </B2CPanelCardHeader>
          <B2CPanelCardBody>
          <div className="space-y-4">
            {" "}
            {feedback.suggested_actions.map((action, index) => (
              <div key={index} className="border-b border-b2c-border pb-4 last:border-b-0 last:pb-0">
                {" "}
                <div className="flex items-start">
                  {" "}
                  <span className="text-osce-accent mr-2">•</span>{" "}
                  <span className="text-osce-ink-900">{action}</span>{" "}
                </div>{" "}
              </div>
            ))}{" "}
          </div>{" "}
          </B2CPanelCardBody>
        </B2CPanelCard>
      )}{" "}
    </div>
  );
};
