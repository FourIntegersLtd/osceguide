"use client";

import { Dropdown } from "@/foundation/table";
import { MarkdownRenderer } from "@/foundation/ui";
import { b2cBodyText, b2cReadingTones, type B2CReadingToneKey } from "@/foundation/ui/productTokens";
import type { InterviewQuestion } from "./model";

export const InfoCard = ({
  title,
  content,
  bgColor = "history",
}: {
  title: string;
  content: string;
  bgColor?: B2CReadingToneKey;
}) => {
  const tone = b2cReadingTones[bgColor] ?? b2cReadingTones.history;
  return (
    <div className={`${tone.card} rounded-osce-lg border p-4`}>
      {" "}
      <h4 className={`mb-2 text-osce-body font-medium ${tone.title}`}>{title}</h4>{" "}
      <div className={b2cBodyText}>
        {" "}
        <MarkdownRenderer content={content} />{" "}
      </div>{" "}
    </div>
  );
};
export const InterviewQuestionsSection = ({
  questions,
}: {
  questions: InterviewQuestion[];
}) => (
  <Dropdown title={`Interview Questions (${questions.length})`}>
    {" "}
    <div className="space-y-3">
      {" "}
      {questions.map((qa, idx) => (
        <Dropdown key={idx} title={`${idx + 1}. ${qa.question}`}>
          {" "}
          <div className={`${b2cReadingTones.tip.card} p-4 rounded-osce-lg border`}>
            {" "}
            <p className={`font-medium ${b2cReadingTones.tip.title} text-osce-body mb-2`}>
              Expected Answer:
            </p>{" "}
            <div className="text-b2c-text-secondary text-osce-body">
              {" "}
              <MarkdownRenderer content={qa.answer} />{" "}
            </div>{" "}
          </div>{" "}
        </Dropdown>
      ))}{" "}
    </div>{" "}
  </Dropdown>
);
