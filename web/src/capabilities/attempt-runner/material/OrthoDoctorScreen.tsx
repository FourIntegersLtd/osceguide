"use client";

import type { AttemptBrief } from "@/capabilities/attempt-runner/api";
import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentList,
  HiOutlinePhoto,
  HiOutlineUsers,
  HiOutlineViewfinderCircle,
} from "react-icons/hi2";
import {
  DoctorInfoSection,
  DoctorInfoShell,
} from "@/capabilities/attempt-runner/material/DoctorInfoLayout";

interface OrthoDoctorScreenProps {
  currentStation?: AttemptBrief["scenario"];
  embedded?: boolean;
}

function OrthoDoctorScreen({
  currentStation,
  embedded = false,
}: OrthoDoctorScreenProps) {
  const stationType = currentStation?.station_type;


  const additionalImages =
    currentStation?.additional_image_urls &&
    currentStation.additional_image_urls.length > 0 ? (
      <DoctorInfoSection
        title="Additional Images"
        icon={HiOutlinePhoto}
        iconTone="orange"
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {currentStation.additional_image_urls.map(
            (imageUrl: string, index: number) => (
              <div key={index} className="flex justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={imageUrl}
                  alt={`Additional image ${index + 1}`}
                  className="h-auto max-w-full rounded-md border border-b2c-border"
                  style={{ maxHeight: "400px" }}
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
              </div>
            ),
          )}
        </div>
      </DoctorInfoSection>
    ) : null;

  if (stationType === "prioritisation") {
    return (
      <DoctorInfoShell embedded={embedded} title="Station information">
        <DoctorInfoSection
          title="Scenario"
          icon={HiOutlineClipboardDocumentList}
          iconTone="primary"
        >
          <p className="whitespace-pre-wrap">
            {currentStation?.clinical_scenario}
          </p>
        </DoctorInfoSection>

        <DoctorInfoSection
          title="Patient List"
          icon={HiOutlineUsers}
          iconTone="emerald"
        >
          <div className="overflow-x-auto">
            <table className="w-full border-collapse border border-b2c-border text-osce-body">
              <thead className="bg-b2c-secondary">
                <tr>
                  {["Patient #", "Age", "Gender", "Summary"].map((label) => (
                    <th
                      key={label}
                      className="border border-b2c-border px-3 py-2 text-left font-semibold text-osce-ink-900"
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {currentStation?.patient_list_for_candidate?.map(
                  (patient, index) => (
                    <tr key={index} className="hover:bg-b2c-secondary">
                      <td className="border border-b2c-border px-3 py-2 text-b2c-text-secondary">
                        {patient.number}
                      </td>
                      <td className="border border-b2c-border px-3 py-2 text-b2c-text-secondary">
                        {patient.age}
                      </td>
                      <td className="border border-b2c-border px-3 py-2 text-b2c-text-secondary">
                        {patient.gender}
                      </td>
                      <td className="border border-b2c-border px-3 py-2 text-b2c-text-secondary">
                        {typeof patient.summary === "string" ? patient.summary : ""}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </DoctorInfoSection>

        {additionalImages}
      </DoctorInfoShell>
    );
  }

  if (stationType === "clinical") {
    return (
      <DoctorInfoShell embedded={embedded} title="Station information">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <DoctorInfoSection
            title="Clinical Scenario"
            icon={HiOutlineClipboardDocumentList}
            iconTone="primary"
            className="border-b-0 pb-0 md:border-b-0"
          >
            <p className="whitespace-pre-wrap">
              {currentStation?.clinical_scenario}
            </p>
          </DoctorInfoSection>

          {currentStation?.radiograph_image_url ? (
            <DoctorInfoSection
              title="Radiograph"
              icon={HiOutlineViewfinderCircle}
              iconTone="sky"
              className="border-b-0 pb-0"
            >
              <div className="flex justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={currentStation.radiograph_image_url}
                  alt="Radiograph"
                  className="h-auto max-w-full rounded-md border border-b2c-border"
                  style={{ maxHeight: "600px" }}
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
              </div>
            </DoctorInfoSection>
          ) : null}
        </div>
        {additionalImages}
      </DoctorInfoShell>
    );
  }

  if (stationType === "communication") {
    return (
      <DoctorInfoShell embedded={embedded} title="Station information">
        <DoctorInfoSection
          title="Scenario"
          icon={HiOutlineChatBubbleLeftRight}
          iconTone="violet"
        >
          <p className="whitespace-pre-wrap">
            {currentStation?.clinical_scenario}
          </p>
        </DoctorInfoSection>
        {additionalImages}
      </DoctorInfoShell>
    );
  }

  if (stationType === "portfolio") {
    return (
      <DoctorInfoShell embedded={embedded} title="Station information">
        <DoctorInfoSection
          title="Scenario"
          icon={HiOutlineClipboardDocumentList}
          iconTone="primary"
        >
          <p className="whitespace-pre-wrap">
            {currentStation?.clinical_scenario}
          </p>
          {currentStation?.duration_minutes != null ? (
            <p className="mt-2 text-osce-body text-b2c-text-muted">
              Duration: {currentStation.duration_minutes} minutes
            </p>
          ) : null}
        </DoctorInfoSection>
      </DoctorInfoShell>
    );
  }

  return (
    <DoctorInfoShell embedded={embedded} title="Station information">
      <p className="text-osce-body text-b2c-text-muted">
        No station information available for this station type.
      </p>
    </DoctorInfoShell>
  );
}

export default OrthoDoctorScreen;
