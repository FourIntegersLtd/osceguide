import type { CSSProperties, ReactNode } from "react";
import {
  HiOutlineInformationCircle,
  HiOutlineLightBulb,
} from "react-icons/hi2";
import {
  ModalBody,
  ModalIcon,
  ModalLead,
  ModalList,
  ModalListRow,
  ModalSection,
  ModalSectionBullets,
  type ModalTone,
} from "@/foundation/ui/ModalSection";
import { ModalTitle } from "@/foundation/ui/ModalContent";
import { cn } from "@/foundation/ui/cn";

/**
 * About / info modal layout for the CASC, PLAB and Ortho dashboards.
 *
 * Renders in the canonical modal language (`ModalSection`) so these read
 * identically to the SCA dashboard about modals. Kept as a named layer because
 * the call sites are written in "about article" terms.
 */

/** Legacy tone names, mapped onto the canonical modal tones. */
const aboutToneMap: Record<string, ModalTone> = {
  muted: "muted",
  sky: "sky",
  blue: "sky",
  accent: "primary",
  amber: "amber",
  developing: "developing",
  green: "competent",
  competent: "competent",
  rose: "development",
  development: "development",
};

export type AboutInfoSectionTone = keyof typeof aboutToneMap;

function toModalTone(tone?: AboutInfoSectionTone): ModalTone {
  return (tone && aboutToneMap[tone]) || "muted";
}

export function AboutInfo({ children }: { children: ReactNode }) {
  return <ModalBody>{children}</ModalBody>;
}

export function AboutInfoHeader({
  title,
  description,
  icon,
  iconTone = "accent",
}: {
  title: string;
  description?: ReactNode;
  icon?: ReactNode;
  iconTone?: AboutInfoSectionTone;
}) {
  return (
    <ModalLead
      title={title}
      description={description}
      icon={icon}
      iconTone={toModalTone(iconTone)}
    />
  );
}

export function AboutInfoSection({
  children,
  title,
  icon,
  tone = "muted",
  className = "",
}: {
  children: ReactNode;
  title?: ReactNode;
  icon?: ReactNode;
  tone?: AboutInfoSectionTone;
  className?: string;
}) {
  const modalTone = toModalTone(tone);
  return (
    <ModalSection
      title={title}
      icon={icon}
      iconTone={modalTone}
      tint={modalTone}
      className={className}
    >
      {children}
    </ModalSection>
  );
}

export function AboutInfoList({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <ModalList className={className}>{children}</ModalList>;
}

export function AboutInfoItem({
  marker,
  title,
  description,
}: {
  marker: ReactNode;
  title: ReactNode;
  description?: ReactNode;
}) {
  return (
    <ModalListRow marker={marker} title={title} description={description} />
  );
}

export function AboutInfoIconMarker({
  children,
  className = "",
  tone = "accent",
}: {
  children: ReactNode;
  className?: string;
  tone?: AboutInfoSectionTone;
}) {
  return (
    <ModalIcon tone={toModalTone(tone)} size="md" className={className}>
      {children}
    </ModalIcon>
  );
}

export function AboutInfoSwatch({
  className,
  style,
}: {
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <span
      className={cn(
        "mt-1.5 inline-block h-2 w-2 shrink-0 rounded-[2px]",
        className ?? "bg-b2c-text-muted",
      )}
      style={style}
      aria-hidden
    />
  );
}

/** Tinted aside with a leading icon. Same surface language as a section body. */
function AboutInfoAside({
  label,
  children,
  icon,
  tone = "accent",
  className = "",
}: {
  label?: string;
  children: ReactNode;
  icon: ReactNode;
  tone?: AboutInfoSectionTone;
  className?: string;
}) {
  const modalTone = toModalTone(tone);
  return (
    <ModalSection tint={modalTone} className={className}>
      <div className="flex items-start gap-3">
        <ModalIcon tone={modalTone} size="sm" className="mt-0.5">
          {icon}
        </ModalIcon>
        <p className="min-w-0 text-osce-meta leading-relaxed text-b2c-text-secondary">
          {label ? (
            <strong className="font-semibold text-osce-ink-900">
              {/[.!?]$/.test(label) ? label : `${label}:`}{" "}
            </strong>
          ) : null}
          {children}
        </p>
      </div>
    </ModalSection>
  );
}

export function AboutInfoCallout({
  label = "Tip",
  children,
  className = "",
  icon,
  tone = "accent",
}: {
  label?: string;
  children: ReactNode;
  className?: string;
  icon?: ReactNode;
  tone?: AboutInfoSectionTone;
}) {
  return (
    <AboutInfoAside
      label={label}
      tone={tone}
      className={className}
      icon={icon ?? <HiOutlineLightBulb className="h-4 w-4" />}
    >
      {children}
    </AboutInfoAside>
  );
}

export function AboutInfoNote({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <AboutInfoAside
      tone="muted"
      className={className}
      icon={<HiOutlineInformationCircle className="h-4 w-4" />}
    >
      {children}
    </AboutInfoAside>
  );
}

export function AboutInfoBullets({
  items,
  className = "",
}: {
  items: ReactNode[];
  className?: string;
}) {
  return <ModalSectionBullets items={items} className={className} />;
}

export function AboutInfoSectionTitle({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <ModalTitle className={className}>{children}</ModalTitle>;
}

export { ModalBody, ModalSection, ModalList, ModalListRow, ModalLead };
