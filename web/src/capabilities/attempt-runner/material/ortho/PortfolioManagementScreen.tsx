"use client";

import { Dropdown } from "@/foundation/table";
import { b2cReadingTones } from "@/foundation/ui/productTokens";
import type { Station } from "./model";
import { InterviewQuestionsSection } from "./OrthoSections";

export const PortfolioManagementScreen = ({
  currentStation,
}: {
  currentStation: Station;
}) => {
  const portfolioThemes = Array.isArray(currentStation.portfolio_themes)
    ? currentStation.portfolio_themes
    : [];
  const keyLearningPoints = Array.isArray(currentStation.key_learning_points)
    ? currentStation.key_learning_points
    : [];
  const references = Array.isArray(currentStation.references)
    ? currentStation.references
    : [];
  return (
    <>
      {" "}
      {portfolioThemes.length > 0 && (
        <Dropdown title={`Portfolio themes (${portfolioThemes.length})`}>
          {" "}
          <div className={`${b2cReadingTones.education.card} p-4 rounded-osce-lg border`}>
            {" "}
            <ul className="list-disc list-inside space-y-2 text-b2c-text-secondary">
              {" "}
              {portfolioThemes.map((theme: string, idx: number) => (
                <li key={idx}>{theme}</li>
              ))}{" "}
            </ul>{" "}
          </div>{" "}
        </Dropdown>
      )}{" "}
      {currentStation.interview_questions &&
        currentStation.interview_questions.length > 0 && (
          <InterviewQuestionsSection
            questions={currentStation.interview_questions}
          />
        )}{" "}
      {keyLearningPoints.length > 0 && (
        <Dropdown title={`Key learning points (${keyLearningPoints.length})`}>
          {" "}
          <div className={`${b2cReadingTones.tip.card} p-4 rounded-osce-lg border`}>
            {" "}
            <ul className="list-disc list-inside space-y-2 text-b2c-text-secondary">
              {" "}
              {keyLearningPoints.map((point: string, idx: number) => (
                <li key={idx}>{point}</li>
              ))}{" "}
            </ul>{" "}
          </div>{" "}
        </Dropdown>
      )}{" "}
      {references.length > 0 && (
        <Dropdown title={`References (${references.length})`}>
          {" "}
          <div className="bg-b2c-surface-muted p-4 rounded-lg">
            {" "}
            <ul className="space-y-2 text-b2c-text-secondary">
              {" "}
              {references.map((ref: string, idx: number) => (
                <li key={idx} className="text-osce-body">
                  {ref}
                </li>
              ))}{" "}
            </ul>{" "}
          </div>{" "}
        </Dropdown>
      )}{" "}
    </>
  );
};
