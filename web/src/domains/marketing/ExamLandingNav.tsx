"use client";

import { HiOutlineArrowRight } from "react-icons/hi2";
import Link from "next/link";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import Logo from "@/foundation/ui/Logo";
import type { ExamKey } from "./landingExams";
import { useLandingVariant } from "./LandingVariantContext";
import { LOGIN_PATH, REGISTER_PATH } from "@/foundation/attribution/partnerConstants";

type ExamLandingNavProps = {
  appType: ExamKey;
  registerLabel?: string;
};

export function ExamLandingNav({
  appType,
  registerLabel = "Register",
}: ExamLandingNavProps) {
  const { type, theme } = useLandingVariant();
  const partner = usePartnerContext();
  const registerHref = partner.href(REGISTER_PATH, appType);
  const loginHref = partner.href(LOGIN_PATH, appType);

  return (
    <header className={theme.navClassName}>
      <div
        className={`${type.sectionShell} flex h-[60px] min-w-0 items-center justify-between gap-2 sm:gap-4`}
      >
        <Link
          href="/"
          className="flex min-w-0 shrink items-center"
          aria-label="Back to OSCE Guide home"
        >
          <Logo variant="light" className="max-sm:scale-[0.92] max-sm:origin-left" />
        </Link>

        <nav className="hidden shrink-0 items-center gap-3 md:flex">
          <Link href={loginHref} className={`${type.navLink} font-medium`}>
            Log in
          </Link>
          <Link href={registerHref} className={`${type.ctaInk} group gap-2`}>
            {registerLabel}
            <HiOutlineArrowRight className="transition-transform group-hover:translate-x-0.5" />
          </Link>
        </nav>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2 md:hidden">
          <Link
            href={loginHref}
            className={`${type.navLink} text-xs font-medium sm:text-[13px]`}
          >
            Log in
          </Link>
          <Link href={registerHref} className={type.ctaInk}>
            {registerLabel}
          </Link>
        </div>
      </div>
    </header>
  );
}
