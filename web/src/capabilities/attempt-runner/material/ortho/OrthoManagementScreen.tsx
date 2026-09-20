"use client";

import { MarkdownRenderer } from "@/foundation/ui";
import { b2cBodyText, b2cSectionTitle, b2cPageTitle } from "@/foundation/ui/productTokens";
import type { Station } from "./model";
import { StationComments } from "@/capabilities/community/StationComments";
import { ClinicalManagementScreen } from "./ClinicalManagementScreen";
import { PrioritisationManagementScreen } from "./PrioritisationManagementScreen";
import { CommunicationManagementScreen } from "./CommunicationManagementScreen";
import { PortfolioManagementScreen } from "./PortfolioManagementScreen";

export const OrthoManagementScreen = ({
  currentStation,
}: {
  currentStation: Station;
}) => {
  const stationType = currentStation.station_type || "clinical";
  const hasImages =
    currentStation.radiograph_image_url ||
    currentStation.additional_image_urls?.length;
  return (
    <div className="space-y-8 select-none">
      {" "}
      <h1 className={`${b2cPageTitle} my-6 text-center`}>
        {currentStation.station_name}
      </h1>{" "}
      <div className="lg:bg-white lg:rounded-lg lg:p-6 lg:">
        {" "}
        <h2 className={`${b2cSectionTitle} mb-4`}>
          Clinical Scenario
        </h2>{" "}
        <div
          className={`rounded-lg border border-osce-accent-subtle bg-osce-accent-muted p-4 ${b2cBodyText}`}
        >
          {" "}
          <MarkdownRenderer
            content={currentStation.clinical_scenario || "No scenario provided"}
          />{" "}
        </div>{" "}
        {hasImages && (
          <div className="mt-6">
            {" "}
            <h3 className={`${b2cSectionTitle} mb-3`}>
              Imaging
            </h3>{" "}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {" "}
              {currentStation.radiograph_image_url && (
                <div className="border border-b2c-border rounded-lg overflow-hidden">
                  {" "}
                  {/* Operator-supplied host, outside next/image remotePatterns. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={currentStation.radiograph_image_url}
                    alt="Primary radiograph"
                    className="w-full h-auto"
                  />{" "}
                </div>
              )}{" "}
              {currentStation.additional_image_urls?.map((url, idx) => (
                <div
                  key={idx}
                  className="border border-b2c-border rounded-lg overflow-hidden"
                >
                  {" "}
                  {/* Operator-supplied host, outside next/image remotePatterns. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={url}
                    alt={`Additional image ${idx + 1}`}
                    className="w-full h-auto"
                  />{" "}
                </div>
              ))}{" "}
            </div>{" "}
          </div>
        )}{" "}
      </div>{" "}
      <div className="lg:bg-white lg:rounded-lg lg:p-6 lg:">
        {" "}
        <h2 className={`${b2cSectionTitle} mb-4`}>
          Management Details
        </h2>{" "}
        {stationType === "clinical" && (
          <ClinicalManagementScreen currentStation={currentStation} />
        )}{" "}
        {stationType === "prioritisation" && (
          <PrioritisationManagementScreen currentStation={currentStation} />
        )}{" "}
        {stationType === "communication" && (
          <CommunicationManagementScreen currentStation={currentStation} />
        )}{" "}
        {stationType === "portfolio" && (
          <PortfolioManagementScreen currentStation={currentStation} />
        )}{" "}
      </div>{" "}
      <StationComments stationId={currentStation.station_id} />{" "}
    </div>
  );
};
export default OrthoManagementScreen;
