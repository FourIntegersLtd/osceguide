"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useSession } from "@/foundation/session";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { b2cButtonPrimary, b2cButtonSecondary } from "@/foundation/ui/productTokens";


type UnauthorizedAccessProps = {
  title?: string;
  description?: string;
};

function UnauthorizedAccess({
  title = "You don't have access to this page",
  description = "If you think you should, sign in with the account that was given access, or contact your OSCE Guide admin.",
}: UnauthorizedAccessProps) {
  const { signOut } = useSession();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const logout = async () => {
    setIsLoggingOut(true);
    try {
      await signOut();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div
      role="alert"
      className="mx-auto flex w-full max-w-xl flex-col items-center gap-4 px-4 py-12 text-center"
    >
      <Image
        src="/images/unauthorized.png"
        alt=""
        aria-hidden
        width={280}
        height={280}
        className="h-auto w-full max-w-[240px]"
      />
      <h1 className="text-osce-title font-semibold text-osce-ink-900">
        {title}
      </h1>
      <p className="max-w-md text-osce-body text-b2c-text-muted">{description}</p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={() => void logout()}
          disabled={isLoggingOut}
          className={b2cButtonPrimary}
        >
          {isLoggingOut ? "Signing out…" : "Sign in with a different account"}
        </button>
        <a href={`mailto:${SUPPORT_EMAIL}`} className={b2cButtonSecondary}>
          Contact support
        </a>
        <Link href="/dashboard" className={b2cButtonSecondary}>
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}

export default UnauthorizedAccess;
