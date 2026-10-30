import Image from "next/image";
import { B2B_IMG } from "../institutionsLandingContent";

type B2bMarketingScreenshotProps = {
  alt: string;
  caption?: string;
  maxHeightClass?: string;
};

export function B2bMarketingScreenshot({ alt, caption, maxHeightClass = "max-h-[min(560px,72vh)]" }: B2bMarketingScreenshotProps) {
  const { src, w, h } = B2B_IMG.dashboard;
  return (
    <figure className="space-y-3">
      <div className="overflow-hidden rounded-2xl border border-site-line bg-site-card shadow-sm">
        <Image
          src={src}
          alt={alt}
          width={w}
          height={h}
          className={`w-full object-cover object-top ${maxHeightClass}`}
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 90vw, 1100px"
        />
      </div>
      {caption ? <figcaption className="text-site-body">{caption}</figcaption> : null}
    </figure>
  );
}
