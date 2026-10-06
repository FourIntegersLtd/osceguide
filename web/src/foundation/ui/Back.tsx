"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GoArrowLeft } from "react-icons/go";

const classes =
  "inline-flex items-center text-b2c-text-secondary hover:text-osce-ink-900 mb-8 group";

/** Back to `href` when the screen has a fixed parent, else one step through the browser history. */
function Back({ href }: { href?: string }) {
  const router = useRouter();
  const content = (
    <>
      <GoArrowLeft className="h-5 w-5 mr-2 group-hover:-translate-x-1 transition-transform" />
      <span>Back</span>
    </>
  );
  return (
    <div>
      {href ? (
        <Link href={href} className={classes}>
          {content}
        </Link>
      ) : (
        <button onClick={() => router.back()} className={classes}>
          {content}
        </button>
      )}
    </div>
  );
}
export default Back;
