import type React from "react";
import { prepareListItem } from "./managementListHelpers";
import { b2cBodyText, b2cReadingTones, b2cSectionTitle, type B2CReadingToneKey } from "@/foundation/ui/productTokens";
export const InfoItem = ({ label, value }: { label: string; value?: string | null }) => (
  <div className={b2cBodyText}>
    <span className="font-medium text-b2c-text-secondary">{label} </span>
    <span>{value || "Not specified"}</span>
  </div>
);

export const ListItems = ({ items, label }: { items?: string[]; label: string }) => (
  <div className="mb-4">
    {label ? (
      <span className={`font-medium ${b2cBodyText}`}>{label}</span>
    ) : null}
    {items && items.length > 0 ? (
      <ul
        className={`list-disc p-2 pl-5 [list-style-position:outside] lg:p-4 ${b2cBodyText}`}
      >
        {items.map((item, index) => {
          const { text, isNumberedHeading } = prepareListItem(item);
          return (
            <li
              key={index}
              className={
                isNumberedHeading
                  ? "mt-3 list-none whitespace-pre-wrap break-words font-semibold text-osce-ink-900 first:mt-0"
                  : "whitespace-pre-wrap break-words"
              }
            >
              {text}
            </li>
          );
        })}
      </ul>
    ) : (
      <p className="mt-1 text-osce-body italic text-b2c-text-muted">
        No items available
      </p>
    )}
  </div>
);

export const InfoCard = ({
  title,
  items,
  bgColor = "history",
  type = "list",
}: {
  title: string;
  items: string[] | string;
  bgColor?: B2CReadingToneKey;
  type?: "list" | "text";
}) => {
  const tone = b2cReadingTones[bgColor] ?? b2cReadingTones.history;
  return (
    <div className={`rounded-2xl border p-4 ${tone.card}`}>
      <h4 className={`mb-2 text-osce-body font-medium ${tone.title}`}>{title}</h4>
      {type === "list" ? (
        <ListItems items={Array.isArray(items) ? items : []} label="" />
      ) : (
        <p className={b2cBodyText}>{items}</p>
      )}
    </div>
  );
};

export const SectionContainer = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => (
  <div className="my-6 space-y-4 sm:my-8 sm:space-y-6">
    <h3 className={`${b2cSectionTitle} border-b border-b2c-border pb-2`}>
      {title}
    </h3>
    {children}
  </div>
);

export const GridLayout = ({
  itemCount,
  children,
}: {
  itemCount: number;
  children: React.ReactNode;
}) => (
  <div
    className={`grid grid-cols-1 gap-6 ${itemCount > 1 ? "2xl:grid-cols-2" : ""}`}
  >
    {children}
  </div>
);
