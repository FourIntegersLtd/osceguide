"use client";

import { HiOutlineCheckCircle, HiOutlinePresentationChartLine } from "react-icons/hi2";
import {
  AboutInfo,
  AboutInfoCallout,
  AboutInfoHeader,
  AboutInfoIconMarker,
  AboutInfoItem,
  AboutInfoList,
  AboutInfoSection,
  AboutInfoSwatch,
  Modal,
} from "@/foundation/ui";
import { chartColors } from "@/foundation/charts";
import { aboutFor } from "@/domains/train/dashboard/aboutCopy";
import type { AboutItem, AboutKey } from "@/domains/train/dashboard/aboutTypes";
import type { ExamConfig } from "@/domains/train/dashboard/examConfig";

/**
 * The three explanatory modals, rendered from the exam's copy table.
 *
 * One component for twelve old ones. The markup is `AboutInfo` exactly as the
 * originals wrote it, so the modals look and read the same; what varies is the
 * sentences and the swatch colours, and both come from configuration.
 */
export function AboutModal({
  config,
  active,
  onClose,
}: {
  config: ExamConfig;
  active: AboutKey | null;
  onClose: () => void;
}) {
  if (!active) return null;

  const content = aboutFor(config.code)[active];

  return (
    <Modal width="600px" height="fit-content" onClose={onClose} title={content.title}>
      <AboutInfo>
        <AboutInfoHeader title={content.title} description={content.description} />
        <AboutInfoSection title={content.sectionTitle} tone={content.sectionTone}>
          <AboutInfoList>
            {content.items.map((item) => (
              <AboutInfoItem
                key={item.title}
                marker={markerFor(item, config)}
                title={item.title}
                description={item.description}
              />
            ))}
          </AboutInfoList>
        </AboutInfoSection>
        {content.callout ? (
          <AboutInfoCallout label={content.callout.label}>{content.callout.text}</AboutInfoCallout>
        ) : null}
      </AboutInfo>
    </Modal>
  );
}

function markerFor(item: AboutItem, config: ExamConfig) {
  switch (item.marker) {
    case "swatch":
      return (
        <AboutInfoSwatch
          style={{
            backgroundColor:
              config.domains.colors?.[item.swatchFor ?? item.title] ?? chartColors.muted,
          }}
        />
      );
    case "success":
      return (
        <AboutInfoIconMarker className="border-osce-success-border bg-osce-success-bg text-osce-success-text">
          <HiOutlineCheckCircle className="h-3.5 w-3.5" />
        </AboutInfoIconMarker>
      );
    case "danger":
      return (
        <AboutInfoIconMarker className="border-osce-danger-border bg-osce-danger-bg text-osce-danger">
          <HiOutlinePresentationChartLine className="h-3.5 w-3.5" />
        </AboutInfoIconMarker>
      );
    case "threshold":
      return (
        <AboutInfoIconMarker className="border-osce-success-border bg-osce-success-bg text-osce-success-text">
          <span className="h-0.5 w-3.5 border-t-2 border-dashed border-osce-success-icon" />
        </AboutInfoIconMarker>
      );
    default:
      return (
        <AboutInfoIconMarker>
          <HiOutlinePresentationChartLine className="h-3.5 w-3.5" />
        </AboutInfoIconMarker>
      );
  }
}
