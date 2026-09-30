"use client";

import Image from "next/image";

export function HeroPoweredByStrip({ centered = false }: { centered?: boolean }) {
  return (
    <div
      className={`flex flex-wrap items-center gap-x-3.5 gap-y-2 border-t border-[color:var(--landing-warm,rgba(16,24,40,0.09))] pt-5 ${
        centered ? "justify-center text-center" : "mt-7 sm:mt-7 sm:pt-[22px]"
      }`}
    >
      <span className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-[color:var(--landing-eyebrow,#8A94A6)]">
        Powered by
      </span>

      <a
        href="https://deepgram.com/"
        target="_blank"
        rel="noopener noreferrer"
        className="group inline-flex items-center gap-2 text-landing-ink-body transition-opacity hover:opacity-80"
      >
        <Image
          src="/images/deepgram_logo.png"
          alt="Deepgram"
          width={26}
          height={26}
          className="h-[26px] w-[26px] object-contain"
        />
        <span className="font-landing-body text-sm">Deepgram</span>
      </a>

      <span className="text-[#C4CBD6]" aria-hidden>·</span>

      <a
        href="https://aws.amazon.com/events/aws-innovate/"
        target="_blank"
        rel="noopener noreferrer"
        className="group inline-flex items-center gap-2 text-landing-ink-body transition-opacity hover:opacity-80"
      >
        <Image
          src="/images/aws_logo.png"
          alt="AWS"
          width={26}
          height={26}
          className="h-[26px] w-[26px] object-contain"
        />
        <span className="font-landing-body text-sm">AWS</span>
      </a>

      <p
        className={`font-landing-body text-[12.5px] leading-relaxed text-b2c-text-secondary ${
          centered ? "mx-auto max-w-[44ch] px-1 text-pretty sm:px-0" : ""
        }`}
      >
        Proud recipient of startup grants from industry leaders in AI and cloud computing
      </p>
    </div>
  );
}
