"use client";
import { LuStethoscope } from "react-icons/lu";
import { HiOutlineChatBubbleLeftRight, HiOutlineClipboardDocumentCheck, HiOutlineClock } from "react-icons/hi2";
import type React from "react";
import { Dropdown } from "@/foundation/table";
import type { CascFeedback as CascFeedbackData, DomainFeedback } from "./cascTypes";
import { CompetencyTable, asCompetency, domainEntries } from "./CascCompetencyTable";
import { FeedbackSection } from "./CascNarrative";
const DomainSection = ({
  domain,
  data,
  icon,
}: {
  domain: string;
  data: { generic_domains: DomainFeedback };
  icon: React.ReactNode;
}) => {
  return (
    <Dropdown title={domain} icon={icon} defaultOpen>
      {" "}
      <div className="space-y-6">
        {" "}
        <CompetencyTable scores={data} title={`${domain} Competencies`} />{" "}
        <FeedbackSection feedback={data.generic_domains} domain={domain} />{" "}
      </div>{" "}
    </Dropdown>
  );
};
function CascFeedback({ feedback }: { feedback: CascFeedbackData }) {
  // Calculate total competencies
  const calculateCompetencies = (data: object) => {
    let total = 0;
    let achieved = 0;
    domainEntries(data).forEach(([key, rawValue]) => {
      const value = asCompetency(rawValue);
      if (key !== "generic_domains" && value) {
        total++;
        if (value.competent) achieved++;
      }
    });
    return { total, achieved };
  };
  const allDomains = {
    history: calculateCompetencies(feedback.history),
    examination: calculateCompetencies(feedback.examination),
    management: calculateCompetencies(feedback.management),
    communication: calculateCompetencies(feedback.communication),
  };
  const totalCompetencies = Object.values(allDomains).reduce(
    (acc, curr) => ({
      total: acc.total + curr.total,
      achieved: acc.achieved + curr.achieved,
    }),
    { total: 0, achieved: 0 },
  );
  return (
    <div className="space-y-6">
      {" "}
      <div className="text-center mb-8">
        {" "}
        {/* Calculate percentage */}{" "}
        {(() => {
          const percentage =
            (totalCompetencies.achieved / totalCompetencies.total) * 100;
          const isGoodScore = percentage >= 80;
          return (
            <div
              className={` Rounded-lg p-6 inline-block ${isGoodScore ? "bg-osce-success-bg" : "bg-osce-danger-bg"} transition-all duration-300 `}
            >
              {" "}
              <p className="text-osce-body flex items-center justify-center gap-3">
                {" "}
                <span>Overall Competencies:</span>{" "}
                <span
                  className={` Font-bold text-osce-subheading ${isGoodScore ? "text-osce-success-text" : "text-osce-danger"} `}
                >
                  {" "}
                  {totalCompetencies.achieved}/{totalCompetencies.total}{" "}
                </span>{" "}
                <span
                  className={` Text-b2c-body ml-2 px-3 py-1 rounded-full ${isGoodScore ? "bg-osce-success-bg text-osce-success-text" : "bg-osce-danger-bg text-osce-danger-hover"} `}
                >
                  {" "}
                  {percentage.toFixed(1)}%{" "}
                </span>{" "}
              </p>{" "}
            </div>
          );
        })()}{" "}
      </div>{" "}
      <div className="space-y-6">
        {" "}
        <DomainSection
          domain="History Taking"
          data={feedback.history}
          icon={<HiOutlineClock className="h-5 w-5" />}
        />{" "}
        <DomainSection
          domain="Examination"
          data={feedback.examination}
          icon={<LuStethoscope className="h-5 w-5" />}
        />{" "}
        <DomainSection
          domain="Management"
          data={feedback.management}
          icon={<HiOutlineClipboardDocumentCheck className="h-5 w-5" />}
        />{" "}
        <DomainSection
          domain="Communication"
          data={feedback.communication}
          icon={<HiOutlineChatBubbleLeftRight className="h-5 w-5" />}
        />{" "}
      </div>{" "}
    </div>
  );
}
export default CascFeedback;
