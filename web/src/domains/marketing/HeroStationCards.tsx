"use client";
import type { ComponentType } from "react";
const CARD_STYLES = [
  {
    bg: "bg-osce-accent-muted",
    border: "border-osce-accent-subtle",
    iconBg: "bg-osce-accent",
    bar: "bg-osce-accent",
    rotate: "-0.5",
  },
  {
    bg: "bg-osce-accent-muted",
    border: "border-osce-accent-subtle",
    iconBg: "bg-osce-accent-hover",
    bar: "bg-osce-accent",
    rotate: "0.5",
  },
  {
    bg: "bg-osce-accent-muted",
    border: "border-osce-accent-subtle",
    iconBg: "bg-osce-accent-hover",
    bar: "bg-osce-accent",
    rotate: "-0.5",
  },
  {
    bg: "bg-osce-surface",
    border: "border-b2c-border",
    iconBg: "bg-osce-accent-light",
    bar: "bg-osce-accent-light",
    rotate: "0.5",
  },
] as const;
export type HeroStationItem = {
  label: string;
  icon?: ComponentType<{ className?: string }>;
};
export type HeroStationCardsProps = { items: Array<HeroStationItem> };
export function HeroStationCards({ items }: HeroStationCardsProps) {
  return (
    <div className="mt-12 flex w-full items-center justify-center lg:mt-0 lg:w-[48%] lg:flex-shrink-0 lg:justify-center">
      {" "}
      <div className="relative w-full max-w-md sm:max-w-lg">
        {" "}
        {/* Soft glow behind panel */}{" "}
        <div className="absolute -inset-1 rounded-[1.375rem] bg-gradient-to-br from-osce-accent-light/25 via-osce-accent-light/15 to-osce-accent-light/25 blur-2xl" />{" "}
        {/* Gradient panel */}{" "}
        <div className="absolute inset-0 rounded-2xl border border-osce-accent-subtle/60 bg-gradient-to-br from-osce-accent-muted/95 via-osce-accent-muted/90 to-osce-accent-muted/95 shadow-inner" />{" "}
        <div className="relative flex flex-col gap-3 p-5 sm:gap-4 sm:p-6">
          {" "}
          {items.map(({ label, icon: Icon }, i) => {
            const style = CARD_STYLES[i % CARD_STYLES.length];
            return (
              <div
                key={label}
                className={`flex min-h-[3.25rem] items-center gap-4 rounded-xl border-2 ${style.border} ${style.bg} px-4 py-3 shadow-md transition-all duration-200 hover:scale-[1.02] hover:shadow-lg sm:min-h-[3.5rem] sm:px-5 sm:py-3.5`}
                style={{ transform: `rotate(${style.rotate}deg)` }}
              >
                {" "}
                {Icon ? (
                  <span
                    className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${style.iconBg} text-white shadow-sm sm:h-10 sm:w-10`}
                  >
                    {" "}
                    <Icon className="h-4 w-4 sm:h-5 sm:w-5" />{" "}
                  </span>
                ) : (
                  <div
                    className={`h-2 w-10 flex-shrink-0 rounded-full sm:w-12 ${style.bar}`}
                  />
                )}{" "}
                <span className="min-w-0 flex-1 font-landing-heading text-sm font-semibold text-osce-ink-900 sm:text-[15px]">
                  {" "}
                  {label}{" "}
                </span>{" "}
              </div>
            );
          })}{" "}
        </div>{" "}
      </div>{" "}
    </div>
  );
}
