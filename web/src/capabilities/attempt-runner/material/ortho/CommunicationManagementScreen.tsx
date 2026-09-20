"use client";

import { Dropdown } from "@/foundation/table";
import { b2cReadingTones, b2cSectionTitle } from "@/foundation/ui/productTokens";
import type { Station } from "./model";
import { InfoCard, InterviewQuestionsSection } from "./OrthoSections";

export const CommunicationManagementScreen = ({
  currentStation,
}: {
  currentStation: Station;
}) => (
  <>
    {" "}
    {currentStation.communication_themes &&
      currentStation.communication_themes.length > 0 && (
        <div className="mb-6">
          {" "}
          <h3 className={`${b2cSectionTitle} mb-3`}>
            💬 Communication Skills Assessed
          </h3>{" "}
          <div className="flex flex-wrap gap-2">
            {" "}
            {currentStation.communication_themes.map((theme, idx) => (
              <span
                key={idx}
                className="px-3 py-1 bg-osce-accent-subtle text-osce-accent-hover rounded-full text-osce-body font-medium"
              >
                {" "}
                {theme}{" "}
              </span>
            ))}{" "}
          </div>{" "}
        </div>
      )}{" "}
    <Dropdown title="Communication Frameworks">
      {" "}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {" "}
        {currentStation.consent_approach && (
          <InfoCard
            title="Consent Approach"
            content={currentStation.consent_approach}
            bgColor="education"
          />
        )}{" "}
        {currentStation.breaking_bad_news_framework && (
          <InfoCard
            title="Breaking Bad News (SPIKES)"
            content={currentStation.breaking_bad_news_framework}
            bgColor="education"
          />
        )}{" "}
      </div>{" "}
    </Dropdown>{" "}
    {currentStation.interview_questions &&
      currentStation.interview_questions.length > 0 && (
        <InterviewQuestionsSection
          questions={currentStation.interview_questions}
        />
      )}{" "}
    {currentStation.professional_conduct_topics &&
      currentStation.professional_conduct_topics.length > 0 && (
        <Dropdown
          title={`Professional Conduct Topics (${currentStation.professional_conduct_topics.length})`}
        >
          {" "}
          <div className={`${b2cReadingTones.education.card} p-4 rounded-osce-lg border`}>
            {" "}
            <ul className="list-disc list-inside space-y-2 text-b2c-text-secondary text-osce-body">
              {" "}
              {currentStation.professional_conduct_topics.map((topic, idx) => (
                <li key={idx}>{topic}</li>
              ))}{" "}
            </ul>{" "}
          </div>{" "}
        </Dropdown>
      )}{" "}
    {currentStation.key_learning_points &&
      currentStation.key_learning_points.length > 0 && (
        <Dropdown
          title={`Key Learning Points (${currentStation.key_learning_points.length})`}
        >
          {" "}
          <div className={`${b2cReadingTones.tip.card} p-4 rounded-osce-lg border`}>
            {" "}
            <ul className="list-disc list-inside space-y-2 text-b2c-text-secondary text-osce-body">
              {" "}
              {currentStation.key_learning_points.map((point, idx) => (
                <li key={idx}>{point}</li>
              ))}{" "}
            </ul>{" "}
          </div>{" "}
        </Dropdown>
      )}{" "}
    {currentStation.references && currentStation.references.length > 0 && (
      <Dropdown title={`References (${currentStation.references.length})`}>
        {" "}
        <div className="bg-b2c-surface-muted p-4 rounded-lg">
          {" "}
          <ul className="space-y-2 text-b2c-text-secondary">
            {" "}
            {currentStation.references.map((ref, idx) => (
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
