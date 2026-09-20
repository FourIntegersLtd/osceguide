"use client";

import { Dropdown } from "@/foundation/table";
import { MarkdownRenderer } from "@/foundation/ui";
import { b2cBodyText, b2cSectionTitle } from "@/foundation/ui/productTokens";
import type { Station } from "./model";
import { InterviewQuestionsSection } from "./OrthoSections";
import { PatientList, TheatreList } from "./OrthoLists";

export const PrioritisationManagementScreen = ({
  currentStation,
}: {
  currentStation: Station;
}) => (
  <>
    {" "}
    {currentStation.background_overview && (
      <div className="bg-osce-accent-muted p-4 rounded-lg border border-osce-accent-subtle mb-6">
        {" "}
        <h3 className={`${b2cSectionTitle} mb-2 text-osce-accent-hover`}>
          📋 Background Context
        </h3>{" "}
        <div className={b2cBodyText}>
          {" "}
          <MarkdownRenderer content={currentStation.background_overview} />{" "}
        </div>{" "}
      </div>
    )}{" "}
    <Dropdown title="Patient Information">
      {" "}
      <div className="grid grid-cols-1 gap-6">
        {" "}
        {currentStation.patient_list_for_candidate && (
          <PatientList
            patients={currentStation.patient_list_for_candidate}
            title="Candidate Patient List"
            bgColor="history"
            showNotes={false}
          />
        )}{" "}
        {currentStation.examiner_additional_info && (
          <PatientList
            patients={currentStation.examiner_additional_info}
            title="Examiner Additional Information"
            bgColor="education"
            showNotes={true}
          />
        )}{" "}
      </div>{" "}
    </Dropdown>{" "}
    {currentStation.suggested_order_overview && (
      <Dropdown title="Prioritisation Approach">
        {" "}
        <div className="bg-osce-accent-muted p-4 rounded-lg border border-osce-accent-subtle">
          {" "}
          <div className="text-b2c-text-secondary text-osce-body">
            {" "}
            <MarkdownRenderer
              content={currentStation.suggested_order_overview}
            />{" "}
          </div>{" "}
        </div>{" "}
      </Dropdown>
    )}{" "}
    {currentStation.suggested_order && (
      <Dropdown title="Detailed List Order">
        {" "}
        <div className="space-y-4">
          {" "}
          {currentStation.suggested_order.cepod_emergency_list && (
            <TheatreList
              items={currentStation.suggested_order.cepod_emergency_list}
              title="CEPOD/Emergency List"
              tone="safety"
            />
          )}{" "}
          {currentStation.suggested_order.theatre_list_1_full_day && (
            <TheatreList
              items={currentStation.suggested_order.theatre_list_1_full_day}
              title="Theatre List 1 (Full Day)"
              tone="management"
            />
          )}{" "}
          {currentStation.suggested_order.theatre_list_2_half_day && (
            <TheatreList
              items={currentStation.suggested_order.theatre_list_2_half_day}
              title="Theatre List 2 (Half Day)"
              tone="history"
            />
          )}{" "}
        </div>{" "}
      </Dropdown>
    )}{" "}
    {currentStation.interview_questions &&
      currentStation.interview_questions.length > 0 && (
        <InterviewQuestionsSection
          questions={currentStation.interview_questions}
        />
      )}{" "}
  </>
);
