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
import type { DashboardView } from "@/domains/train/dashboard/dashboardView";

/**
 * The three explanatory modals, rendered from the exam's copy table.
 *
 * One component for twelve old ones. The markup is `AboutInfo` exactly as the
 * originals wrote it; the sentences and swatch colours come from the same
 * dashboard view the charts draw, so they quote the same scale.
 */
export function AboutModal({
  view,
  active,
  onClose,
}: {
  view: DashboardView;
  active: AboutKey | null;
  onClose: () => void;
}) {
  if (!active) return null;

  const content = aboutFor(view)[active];

  return (
    <Modal width="600px" height="fit-content" onClose={onClose} title={content.title}>
      <AboutInfo>
        <AboutInfoHeader title={content.title} description={content.description} />
        <AboutInfoSection title={content.sectionTitle} tone={content.sectionTone}>
          <AboutInfoList>
            {content.items.map((item) => (
              <AboutInfoItem
                key={item.title}
                marker={markerFor(item)}
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

function markerFor(item: AboutItem) {
  switch (item.marker) {
    case "swatch":
      return (
        <AboutInfoSwatch
          style={{ backgroundColor: item.color ?? chartColors.muted }}
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
