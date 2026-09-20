"use client";

import React, { useState } from "react";
import type { IconType } from "react-icons";
import {
  HiOutlineBookOpen,
  HiOutlineChatBubbleLeftEllipsis,
  HiOutlineClipboardDocumentList,
  HiOutlineExclamationTriangle,
  HiOutlineHandRaised,
  HiOutlineInformationCircle,
  HiOutlineLightBulb,
  HiOutlineNewspaper,
  HiOutlineQuestionMarkCircle,
  HiOutlineUser,
  HiOutlineUsers,
} from "react-icons/hi2";
import { ModalBullets, ModalCallout } from "@/foundation/ui/ModalContent";
import { B2CSegmentedTabs } from "@/foundation/ui/B2CSegmentedTabs";
import {
  B2CSectionIconBadge,
  type B2CSectionIconTone,
} from "@/foundation/ui/B2CSectionIconBadge";
import { DoctorInfoSection } from "@/capabilities/attempt-runner/material/DoctorInfoLayout";
import {
  b2cReadingTones,
  b2cSectionTitle,
  b2cGroupedRowSubtitle,
} from "@/foundation/ui/productTokens";
import type { PatientRoleplay as PatientInformation } from "@/capabilities/debrief/api";

interface PatientPreparationProps {
  stationData?: { patient_information?: Partial<PatientInformation> };
  noBorder?: boolean;
}

type TabId = "history" | "ice" | "persona";

const TABS: { id: TabId; label: string; icon: IconType }[] = [
  { id: "history", label: "History", icon: HiOutlineClipboardDocumentList },
  { id: "ice", label: "ICE & Concerns", icon: HiOutlineLightBulb },
  { id: "persona", label: "Persona", icon: HiOutlineInformationCircle },
];

function splitListLines(text: string | null | undefined): string[] | null {
  if (!text?.trim()) return null;
  const lines = text
    .split(/\n+/)
    .map((line) => line.replace(/^[\s•\-–]+/, "").trim())
    .filter(Boolean);
  return lines.length > 1 ? lines : null;
}

export function PatientRoleplayScript({
  stationData,
  noBorder = false,
}: PatientPreparationProps) {
  const [activeTab, setActiveTab] = useState<TabId>("history");
  const patientInfo = stationData?.patient_information || {};
  const storyLines = splitListLines(patientInfo?.expanded_history);
  const personaLines = splitListLines(patientInfo?.persona);

  const tabItems = TABS.map((tab) => {
    const TabIcon = tab.icon;
    return {
      id: tab.id,
      label: (
        <span className="inline-flex items-center gap-2">
          <TabIcon className="h-4 w-4 shrink-0" aria-hidden />
          {tab.label}
        </span>
      ),
    };
  });

  return (
    <div
      className={`flex h-full flex-col overflow-hidden bg-osce-surface text-osce-body ${noBorder ? "" : "rounded-osce-lg border border-b2c-border"}`}
    >
      <div className="shrink-0 px-4 pt-4 sm:px-5">
        <div className="flex items-center gap-2.5">
          <B2CSectionIconBadge tone="violet">
            <HiOutlineUser aria-hidden />
          </B2CSectionIconBadge>
          <div className="min-w-0">
            <h3 className={b2cSectionTitle}>Patient roleplay script</h3>
            <p className={`${b2cGroupedRowSubtitle} truncate`}>
              {patientInfo?.patient_biodata || "Standard Patient"}
            </p>
          </div>
        </div>
        <B2CSegmentedTabs
          className="mt-3"
          aria-label="Patient script sections"
          items={tabItems}
          value={activeTab}
          onChange={setActiveTab}
        />
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
        {activeTab === "history" && (
          <>
            <DoctorInfoSection
              title="Your opening sentence"
              icon={HiOutlineChatBubbleLeftEllipsis}
              iconTone="primary"
              emphasize
            >
              <p className="italic">
                &quot;
                {patientInfo?.opening_sentence ||
                  "No opening sentence provided"}
                &quot;
              </p>
            </DoctorInfoSection>

            <DoctorInfoSection
              title="The story (details to give if asked)"
              icon={HiOutlineBookOpen}
              iconTone="sky"
            >
              {storyLines ? (
                <ModalBullets tone="primary" items={storyLines} />
              ) : (
                <p className="whitespace-pre-wrap">
                  {patientInfo?.expanded_history ||
                    "No history details available."}
                </p>
              )}
            </DoctorInfoSection>

            {patientInfo?.family_social_history &&
              patientInfo.family_social_history.length > 0 && (
                <DoctorInfoSection
                  title="Background"
                  icon={HiOutlineUsers}
                  iconTone="emerald"
                >
                  <ModalBullets
                    tone="primary"
                    items={patientInfo.family_social_history}
                  />
                </DoctorInfoSection>
              )}

            {patientInfo?.past_med_history_allergies &&
              patientInfo.past_med_history_allergies.length > 0 && (
                <DoctorInfoSection
                  title="Medical history"
                  icon={HiOutlineNewspaper}
                  iconTone="rose"
                >
                  <ModalBullets
                    tone="primary"
                    items={patientInfo.past_med_history_allergies}
                  />
                </DoctorInfoSection>
              )}
          </>
        )}

        {activeTab === "ice" && (
          <>
            {(
              [
                {
                  label: "Ideas",
                  items: patientInfo?.idea,
                  icon: HiOutlineLightBulb,
                  iconTone: "amber" as B2CSectionIconTone,
                },
                {
                  label: "Concerns",
                  items: patientInfo?.concerns,
                  icon: HiOutlineExclamationTriangle,
                  iconTone: "rose" as B2CSectionIconTone,
                },
                {
                  label: "Expectations",
                  items: patientInfo?.expectation,
                  icon: HiOutlineHandRaised,
                  iconTone: "violet" as B2CSectionIconTone,
                },
              ] as const
            ).map((group) => (
              <DoctorInfoSection
                key={group.label}
                title={group.label}
                icon={group.icon}
                iconTone={group.iconTone}
              >
                {group.items && group.items.length > 0 ? (
                  <ModalBullets tone="primary" items={group.items} />
                ) : (
                  <p className="italic text-b2c-text-muted">
                    No information provided.
                  </p>
                )}
              </DoctorInfoSection>
            ))}

            {patientInfo?.questions && patientInfo.questions.length > 0 && (
              <DoctorInfoSection
                title="Questions you may ask"
                icon={HiOutlineQuestionMarkCircle}
                iconTone="orange"
              >
                <ul
                  className={`list-disc space-y-2 pl-5 marker:text-osce-warning-text ${b2cReadingTones.practice.body}`}
                >
                  {patientInfo.questions.map((q, i) => (
                    <li
                      key={i}
                      className={`rounded-osce-md border px-3 py-2.5 font-medium leading-snug ${b2cReadingTones.practice.card}`}
                    >
                      {q}
                    </li>
                  ))}
                </ul>
              </DoctorInfoSection>
            )}
          </>
        )}

        {activeTab === "persona" && (
          <>
            <DoctorInfoSection
              title="Your personality & approach"
              icon={HiOutlineUser}
              iconTone="primary"
            >
              {personaLines ? (
                <ModalBullets tone="primary" items={personaLines} />
              ) : (
                <p className="italic">
                  {patientInfo?.persona || "No persona information provided."}
                </p>
              )}
            </DoctorInfoSection>
            <ModalCallout className="mt-0">
              Respond naturally to the doctor&apos;s questions and share your
              thoughts, concerns, and expectations.
            </ModalCallout>
          </>
        )}
      </div>
    </div>
  );
}
