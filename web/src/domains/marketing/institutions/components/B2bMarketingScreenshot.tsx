import Image from "next/image";
import { B2B_IMG } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";

type B2bMarketingScreenshotProps = {
  alt: string;
  caption?: string;
  priority?: boolean;
  maxHeightClass?: string;
};

export function B2bMarketingScreenshot({
  alt,
  caption,
  priority = false,
  maxHeightClass = "max-h-[min(560px,72vh)]",
}: B2bMarketingScreenshotProps) {
  const type = institutionsLandingType;
  const { src, w, h } = B2B_IMG.dashboard;

  return (
    <figure className="space-y-2">
      <div className="overflow-hidden rounded-landing-panel border border-landing-warm bg-landing-card shadow-landing-showcase">
        <Image
          src={src}
          alt={alt}
          width={w}
          height={h}
          priority={priority}
          className={`w-full object-cover object-top ${maxHeightClass}`}
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 90vw, 1100px"
        />
      </div>
      {caption ? (
        <figcaption className={`${type.itemBody} text-b2c-text-secondary`}>
          {caption}
        </figcaption>
      ) : null}
    </figure>
  );
}
