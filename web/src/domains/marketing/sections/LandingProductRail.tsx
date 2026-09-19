"use client";

import Link from "next/link";
import { useCallback, useRef } from "react";
import { useLandingVariant } from "../LandingVariantContext";
import { landingIconPalette } from "../landingIconPalette";
import { LANDING_PRODUCT_RAIL } from "./landingProductRailContent";
import { LandingProductRailVisual } from "./LandingProductRailVisual";

const SCROLL_GAP_PX = 16;

export function LandingProductRail() {
  const { type } = useLandingVariant();
  const railRef = useRef<HTMLDivElement>(null);

  const scrollRail = useCallback((direction: "prev" | "next") => {
    const rail = railRef.current;
    if (!rail) {
      return;
    }
    const card = rail.querySelector("article");
    const step = card
      ? card.getBoundingClientRect().width + SCROLL_GAP_PX
      : 340;
    rail.scrollBy({
      left: direction === "next" ? step : -step,
      behavior: "smooth",
    });
  }, []);

  return (
    <div className="mt-11 border-t border-landing-hairline pt-11">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-[color:var(--landing-eyebrow,#8A94A6)]">
            Inside the product
          </p>
          <h3 className="mt-3 font-landing-heading text-[20px] font-semibold leading-[1.25] tracking-[-0.025em] text-osce-ink-900 sm:text-[22px]">
            Everything a practice week needs
          </h3>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => scrollRail("prev")}
            className="flex h-[38px] w-[38px] items-center justify-center rounded-full border border-landing-warm-strong bg-landing-card font-landing-body text-sm text-landing-ink-body shadow-landing-card transition-colors hover:border-osce-accent hover:text-osce-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas"
            aria-label="Previous product cards"
          >
            ←
          </button>
          <button
            type="button"
            onClick={() => scrollRail("next")}
            className="flex h-[38px] w-[38px] items-center justify-center rounded-full border border-landing-warm-strong bg-landing-card font-landing-body text-sm text-landing-ink-body shadow-landing-card transition-colors hover:border-osce-accent hover:text-osce-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas"
            aria-label="Next product cards"
          >
            →
          </button>
        </div>
      </div>

      <div
        ref={railRef}
        className="-mx-5 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth px-5 pb-1 [-ms-overflow-style:none] [scrollbar-width:none] sm:mx-0 sm:gap-5 sm:px-0 [&::-webkit-scrollbar]:hidden"
      >
        {LANDING_PRODUCT_RAIL.map((item) => (
          <article
            key={item.id}
            className="w-[calc(100vw-4.25rem)] shrink-0 snap-start overflow-hidden rounded-landing-card border border-landing-warm bg-landing-card shadow-landing-card transition-shadow hover:shadow-landing-card-hover sm:w-[340px]"
          >
            <LandingProductRailVisual item={item} />
            <div className="px-5 py-[18px]">
              <div className="flex items-center gap-2.5">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: landingIconPalette[item.color] }}
                  aria-hidden
                />
                <h4 className="font-landing-heading text-base font-semibold leading-[1.3] tracking-[-0.02em] text-osce-ink-900">
                  {item.title}
                </h4>
              </div>
              <p className={`mt-1.5 ${type.itemBody}`}>{item.description}</p>
              <Link
                href={item.href}
                className={`mt-3.5 inline-block text-[13.5px] ${type.linkAction}`}
              >
                Learn more →
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
