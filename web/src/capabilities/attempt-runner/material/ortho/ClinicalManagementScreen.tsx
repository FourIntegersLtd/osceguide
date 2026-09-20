"use client";

import { Dropdown } from "@/foundation/table";
import { MarkdownRenderer } from "@/foundation/ui";
import { b2cBodyText, b2cReadingTones, b2cSectionTitle } from "@/foundation/ui/productTokens";
import type { Station } from "./model";
import { InfoCard, InterviewQuestionsSection } from "./OrthoSections";

export const ClinicalManagementScreen = ({
  currentStation,
}: {
  currentStation: Station;
}) => (
  <>
    {" "}
    {currentStation.key_concerns && currentStation.key_concerns.length > 0 && (
      <div className={`${b2cReadingTones.safety.card} p-4 rounded-osce-lg border mb-6`}>
        {" "}
        <h3 className={`${b2cSectionTitle} mb-2 ${b2cReadingTones.safety.title}`}>
          ⚠️ Key Concerns
        </h3>{" "}
        <div className={b2cBodyText}>
          {" "}
          <MarkdownRenderer
            content={currentStation.key_concerns.join("\n")}
          />{" "}
        </div>{" "}
      </div>
    )}{" "}
    <Dropdown title="Clinical Workflow">
      {" "}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {" "}
        {currentStation.history_overview && (
          <InfoCard
            title="History Taking"
            content={currentStation.history_overview}
            bgColor="history"
          />
        )}{" "}
        {currentStation.examination_overview && (
          <InfoCard
            title="Examination"
            content={currentStation.examination_overview}
            bgColor="examination"
          />
        )}{" "}
        {currentStation.investigations_overview && (
          <InfoCard
            title="Investigations"
            content={currentStation.investigations_overview}
            bgColor="examination"
          />
        )}{" "}
        {currentStation.management_overview && (
          <InfoCard
            title="Management"
            content={currentStation.management_overview}
            bgColor="management"
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
