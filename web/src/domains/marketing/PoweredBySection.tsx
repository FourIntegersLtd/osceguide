"use client";

import Image from "next/image";
import { useLandingVariant } from "./LandingVariantContext";

export function PoweredBySection() {
  const { type, accent } = useLandingVariant();

  return (
    <section className="bg-gradient-to-br from-white to-slate-50 py-16">
      <div className="mx-auto w-full max-w-osce-page px-5 sm:px-7">
        <div className="mx-auto max-w-5xl">
          <div className="mb-4 text-center">
            <p className={type.eyebrow}>Powered By</p>
            <div
              className={`mx-auto h-1 w-16 rounded-full sm:w-20 bg-gradient-to-r ${accent.gradient}`}
            />
          </div>

          <div className="flex flex-col items-center justify-center gap-4 md:flex-row">
            <a
              href="https://deepgram.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="group w-full transform cursor-pointer transition-all duration-300 hover:scale-105 md:w-auto"
            >
              <div className="flex items-center justify-center gap-3 rounded-2xl p-4 transition-shadow hover:shadow-lg sm:gap-4 sm:p-6 md:justify-start">
                <Image
                  src="/images/deepgram_logo.png"
                  alt="Deepgram Logo"
                  width={50}
                  height={50}
                  className="h-[50px] w-[50px] object-contain sm:h-[70px] sm:w-[70px]"
                />
                <div className="flex flex-col">
                  <span
                    className={`${type.itemTitle} transition-colors group-hover:text-osce-accent-hover`}
                  >
                    Deepgram
                  </span>
                  <span className="text-slate-500">Voice AI Partner</span>
                </div>
              </div>
            </a>

            <a
              href="https://aws.amazon.com/events/aws-innovate/"
              target="_blank"
              rel="noopener noreferrer"
              className="group w-full transform cursor-pointer transition-all duration-300 hover:scale-105 md:w-auto"
            >
              <div className="flex items-center justify-center gap-1 rounded-2xl px-4 transition-shadow hover:shadow-lg md:justify-start">
                <Image
                  src="/images/aws_logo.png"
                  alt="AWS Logo"
                  width={70}
                  height={70}
                  className="h-[120px] w-[120px] object-contain"
                />
                <div className="flex flex-col">
                  <span
                    className={`${type.itemTitle} transition-colors group-hover:text-osce-accent-hover`}
                  >
                    AWS
                  </span>
                  <span className="text-slate-500">Cloud Partner</span>
                </div>
              </div>
            </a>
          </div>

          <div className="px-4 text-center">
            <p className={`${type.itemBody} inline-block rounded-md px-4 sm:px-6`}>
              Proud recipient of startup grants from industry leaders in AI and
              cloud computing
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
