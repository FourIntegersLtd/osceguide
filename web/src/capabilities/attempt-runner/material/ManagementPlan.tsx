"use client";

import type { AttemptReview } from "@/capabilities/attempt-runner/api";
import OrthoManagementScreen from "./ortho/OrthoManagementScreen";
import { stationForReview } from "./ortho/model";
import { StationComments } from "@/capabilities/community/StationComments";
import { Dropdown } from "@/foundation/table";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  B2CPanelCardHeaderIcon,
} from "@/foundation/ui";
import {
  b2cPageTitle,
} from "@/foundation/ui/productTokens";
import {
  HiOutlineClipboardDocumentList,
  HiOutlineLightBulb,
  HiOutlineUser,
} from "react-icons/hi2";

import { InfoItem, ListItems, InfoCard, SectionContainer, GridLayout } from "./ManagementSections";
export function ManagementPlan({ review }: { review: Pick<AttemptReview, "exam_code" | "station_title" | "station_id" | "patient_information" | "management_plan" | "scenario" | "teaching"> }) {
  if (review.exam_code === "ortho") return <OrthoManagementScreen currentStation={stationForReview(review)} />;
  const currentStation = { station_name: review.station_title, patient_information: review.patient_information ?? {} };
  const mp = review.management_plan ?? {};
  return (
    <div className="max-w-full select-none space-y-6 overflow-x-hidden sm:space-y-8">
      <h1 className={`${b2cPageTitle} my-4 text-center sm:my-6`}>
        {currentStation.station_name}
      </h1>

      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <B2CPanelCardHeaderIcon icon={HiOutlineUser} tone="emerald" />
          Patient information
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-6">
          <InfoItem
            label="Biodata"
            value={currentStation.patient_information.patient_biodata}
          />
          <div className="rounded-2xl border border-b2c-border bg-osce-accent-muted p-4">
            <h3 className="mb-2 flex items-center gap-1.5 text-osce-body font-medium text-osce-accent-hover">
              <HiOutlineLightBulb className="h-4 w-4 shrink-0" aria-hidden />
              ICE (Ideas, Concerns, Expectations)
            </h3>
            <ListItems
              items={currentStation.patient_information.idea}
              label="Ideas"
            />
            <ListItems
              items={currentStation.patient_information.concerns}
              label="Concerns"
            />
            <ListItems
              items={currentStation.patient_information.expectation}
              label="Expectations"
            />
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>

      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <B2CPanelCardHeaderIcon
            icon={HiOutlineClipboardDocumentList}
            tone="primary"
          />
          Management plan
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-4">
          {mp.explanation ? (
            <InfoCard
              title="Explanation"
              items={mp.explanation}
              type="text"
              bgColor="education"
            />
          ) : null}

          {((mp.differential_diagnosis || []).length > 0 ||
            (mp.examination_findings || []).length > 0 ||
            (mp.assessment || []).length > 0 ||
            (mp.further_investigations || []).length > 0) && (
            <SectionContainer title="Clinical Assessment">
              <GridLayout
                itemCount={
                  [
                    mp.differential_diagnosis,
                    mp.examination_findings,
                    mp.assessment,
                    mp.further_investigations,
                  ].filter((item) => item && item?.length > 0).length
                }
              >
                {(mp.differential_diagnosis || []).length > 0 && (
                  <InfoCard
                    title="Differential Diagnosis"
                    items={mp.differential_diagnosis || []}
                    bgColor="reasoning"
                  />
                )}
                {(mp.examination_findings || []).length > 0 && (
                  <InfoCard
                    title="Examination Findings"
                    items={mp.examination_findings || []}
                    bgColor="examination"
                  />
                )}
                {(mp.assessment || []).length > 0 && (
                  <InfoCard
                    title="Assessment Steps"
                    items={mp.assessment || []}
                    bgColor="reasoning"
                  />
                )}
                {(mp.further_investigations || []).length > 0 && (
                  <InfoCard
                    title="Further Investigations"
                    items={mp.further_investigations || []}
                    bgColor="examination"
                  />
                )}
              </GridLayout>
            </SectionContainer>
          )}

          {((mp.social_concerns?.length || 0) > 0 ||
            (mp.ice?.length || 0) > 0) && (
            <Dropdown title="Social & Patient Concerns" className="mt-0">
              <GridLayout
                itemCount={
                  (mp.social_concerns?.length || 0) + (mp.ice?.length || 0)
                }
              >
                {(mp.social_concerns || []).length > 0 && (
                  <InfoCard
                    title="Social Concerns"
                    items={mp.social_concerns || []}
                    bgColor="history"
                  />
                )}
                {(mp.ice || []).length > 0 && (
                  <InfoCard
                    title="ICE Response"
                    items={mp.ice || []}
                    bgColor="history"
                  />
                )}
              </GridLayout>
            </Dropdown>
          )}

          {((mp.immediate_actions?.length ?? 0) > 0 ||
            (mp.pharmacological_treatment?.length ?? 0) > 0 ||
            (mp.non_pharmacological_treatment?.length ?? 0) > 0) && (
            <Dropdown title="Treatment & Actions" className="mt-0">
              <GridLayout
                itemCount={
                  (mp.immediate_actions?.length || 0) +
                  (mp.pharmacological_treatment?.length || 0) +
                  (mp.non_pharmacological_treatment?.length || 0)
                }
              >
                {(mp.immediate_actions || []).length > 0 && (
                  <InfoCard
                    title="Immediate Actions"
                    items={mp.immediate_actions || []}
                    bgColor="safety"
                  />
                )}
                {(mp.pharmacological_treatment || []).length > 0 && (
                  <InfoCard
                    title="Medications"
                    items={mp.pharmacological_treatment || []}
                    bgColor="management"
                  />
                )}
                {(mp.non_pharmacological_treatment || []).length > 0 && (
                  <InfoCard
                    title="Non-Pharmacological Treatment"
                    items={mp.non_pharmacological_treatment || []}
                    bgColor="management"
                  />
                )}
              </GridLayout>
            </Dropdown>
          )}

          {((mp.health_education && mp.health_education?.length > 0) ||
            mp.follow_up ||
            mp.safety_netting ||
            mp.additional_notes) && (
            <Dropdown title="Patient Education & Follow-up" className="mt-0">
              <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
                {(mp.health_education || []).length > 0 && (
                  <InfoCard
                    title="Health Education"
                    items={mp.health_education || []}
                    bgColor="education"
                  />
                )}
                {(mp.follow_up || mp.safety_netting || mp.additional_notes) && (
                  <InfoCard
                    title="Follow-up & Safety"
                    items={[
                      mp.follow_up || "",
                      mp.safety_netting || "",
                      mp.additional_notes || "",
                    ].filter(Boolean)}
                    bgColor="safety"
                  />
                )}
              </div>
            </Dropdown>
          )}

          {mp.additional_notes ? (
            <Dropdown title="Additional Notes" className="mt-0">
              <InfoCard
                title="Additional Notes"
                items={[mp.additional_notes]}
                bgColor="education"
              />
            </Dropdown>
          ) : null}
        </B2CPanelCardBody>
      </B2CPanelCard>

      <StationComments stationId={review.station_id} />
    </div>
  );
}
