"use client";

import { HiOutlinePresentationChartLine } from "react-icons/hi2";
import { useState } from "react";
import Image from "next/image";
import { AnimatePresence, motion } from "framer-motion";
import { NAV_LINKS } from "@/domains/marketing/support/constants";

function navIcon(key: string) {
  const link = NAV_LINKS.find((nav) => nav.key === key);
  if (!link) {
    throw new Error(`Missing nav icon for key: ${key}`);
  }
  return link.icon;
}

type HeroScreenshotTab = {
  id: string;
  label: string;
  src: string;
  alt: string;
  width: number;
  height: number;
  icon: typeof HiOutlinePresentationChartLine;
};

const HERO_SCREENSHOT_TABS = [
  {
    id: "dashboard",
    label: "Dashboard",
    src: "/images/screenshots/dashboard.png",
    alt: "OSCE Guide dashboard with consultation progress and stats",
    width: 2314,
    height: 1554,
    icon: navIcon("dashboard"),
  },
  {
    id: "a-to-z",
    label: "A to Z",
    src: "/images/screenshots/a-to-z.png",
    alt: "OSCE Guide A to Z clinical reference library",
    width: 3024,
    height: 1866,
    icon: navIcon("summary"),
  },
  {
    id: "slides",
    label: "Slides",
    src: "/images/screenshots/slides.png",
    alt: "OSCE Guide video slides by clinical topic",
    width: 3008,
    height: 1884,
    icon: navIcon("slides"),
  },
  {
    id: "marketplace",
    label: "Marketplace",
    src: "/images/screenshots/marketplace.png",
    alt: "OSCE Guide marketplace for booking practice sessions",
    width: 3016,
    height: 1888,
    icon: navIcon("marketplace"),
  },
] satisfies readonly [HeroScreenshotTab, ...HeroScreenshotTab[]];

export function HeroScreenshotShowcase() {
  // The tuple type above is what makes `[0]` a tab rather than a maybe-tab.
  const [activeId, setActiveId] = useState(HERO_SCREENSHOT_TABS[0].id);
  const activeTab =
    HERO_SCREENSHOT_TABS.find((tab) => tab.id === activeId) ?? HERO_SCREENSHOT_TABS[0];

  return (
    <div className="mx-auto w-full">
      <div
        className="overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)] sm:rounded-2xl"
      >
        <div
          className="flex items-center gap-1 overflow-x-auto bg-slate-50/90 px-2 py-2 [-ms-overflow-style:none] [scrollbar-width:none] sm:gap-2 sm:px-3 sm:py-2.5 [&::-webkit-scrollbar]:hidden"
          role="tablist"
          aria-label="Product screenshots"
        >
          {HERO_SCREENSHOT_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = tab.id === activeId;

            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-controls={`hero-screenshot-panel-${tab.id}`}
                id={`hero-screenshot-tab-${tab.id}`}
                onClick={() => setActiveId(tab.id)}
                className={`flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-all sm:px-4 sm:py-2.5 ${
                  isActive
                    ? "border-slate-200/80 bg-white text-neutral-900 shadow-none"
                    : "border-transparent bg-transparent text-neutral-500 hover:bg-white/70 hover:text-neutral-700"
                }`}
              >
                <Icon
                  className={`h-3.5 w-3.5 shrink-0 sm:h-4 sm:w-4 ${
                    isActive ? "text-osce-accent" : "text-neutral-400"
                  }`}
                  aria-hidden
                />
                <span className="whitespace-nowrap">{tab.label}</span>
              </button>
            );
          })}
        </div>

        <div
          id={`hero-screenshot-panel-${activeTab.id}`}
          role="tabpanel"
          aria-labelledby={`hero-screenshot-tab-${activeTab.id}`}
          className="relative bg-white"
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              <Image
                src={activeTab.src}
                alt={activeTab.alt}
                width={activeTab.width}
                height={activeTab.height}
                className="pointer-events-none h-auto w-full select-none object-cover object-top"
                priority={activeTab.id === "dashboard"}
              />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
