import Image from "next/image";

/** Who powers the product and the grants behind it, under the first screen of the landing and the exam pages. */
export function PoweredBy() {
  return (
    <div className="mx-auto mt-12 flex max-w-3xl flex-wrap items-center justify-center gap-x-4 gap-y-3 text-sm text-site-muted">
      <b className="font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-faint">Powered by</b>
      <a
        href="https://deepgram.com/"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center rounded-lg border border-site-line bg-white px-3 py-2"
      >
        <Image src="/images/deepgram_logo.png" alt="Deepgram" width={96} height={28} className="h-7 w-auto" />
      </a>
      <a
        href="https://aws.amazon.com/events/aws-innovate/"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center rounded-lg border border-site-line bg-white px-3 py-2"
      >
        <Image src="/images/aws_logo.png" alt="AWS" width={64} height={34} className="h-7 w-auto" />
      </a>
      <span>Proud recipient of startup grants from industry leaders in AI and cloud computing</span>
    </div>
  );
}
