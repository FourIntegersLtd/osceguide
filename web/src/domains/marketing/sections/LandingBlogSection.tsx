"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchLandingBlogs } from "@/domains/marketing/support/landingBlogs";
import type { Blog } from "@/domains/marketing/support/blog";
import { blogExcerpt, blogReadMinutes } from "@/domains/marketing/support/blogExcerpt";
import { formatApiUtcLocaleDateString } from "@/domains/marketing/support/utcDate";
import { landingSectionSurfaces } from "../landingSectionSurfaces";
import { useLandingVariant } from "../LandingVariantContext";

const CARD_COUNT = 3;

export function LandingBlogSection() {
  const { type } = useLandingVariant();
  const [blogs, setBlogs] = useState<Blog[]>([]);

  useEffect(() => {
    let cancelled = false;

    fetchLandingBlogs(CARD_COUNT)
      .then((data) => {
        if (cancelled) {
          return;
        }
        // Published is approved: a draft is 404 to everyone but an admin.
        const approved = Array.isArray(data)
          ? data
          : [];
        setBlogs(approved.slice(0, CARD_COUNT));
      })
      .catch(() => {
        if (!cancelled) {
          setBlogs([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Nothing published yet — don't leave a hole in the page rhythm.
  if (blogs.length === 0) {
    return null;
  }

  return (
    <section
      id="blog"
      className={`scroll-mt-20 ${landingSectionSurfaces.blog} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div className="max-w-[56ch]">
            <p className={type.eyebrow}>From the blog</p>
            <h2 className={`mt-3 ${type.sectionTitle}`}>
              SCA guidance, written by GPs
            </h2>
            <p className={type.sectionSubtitle}>
              Station breakdowns, marking-domain explainers, and revision
              strategy for the RCGP SCA.
            </p>
          </div>
          <Link href="/blogs" className={`${type.linkAction} shrink-0`}>
            All articles →
          </Link>
        </div>

        <div className="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
          {blogs.map((blog) => (
            <article key={blog.blog_id} className="flex">
              <Link
                href={`/blogs/${blog.url ?? blog.blog_id}`}
                className="group flex w-full flex-col rounded-landing-card border border-landing-warm bg-landing-card px-5 py-[18px] shadow-landing-card transition-[border-color,box-shadow] hover:border-osce-accent hover:shadow-landing-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas"
              >
                <p className={type.eyebrow}>
                  <time dateTime={blog.created_at}>
                    {formatApiUtcLocaleDateString(blog.created_at, "en-GB", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </time>
                  <span aria-hidden> · </span>
                  {blogReadMinutes(blog.content)} min read
                </p>
                <h3
                  className={`mt-3 line-clamp-2 ${type.itemTitle} transition-colors group-hover:text-osce-accent`}
                >
                  {blog.title}
                </h3>
                <p className={`mt-2 line-clamp-3 ${type.itemBody}`}>
                  {blogExcerpt(blog.content)}
                </p>
                <span
                  className={`mt-auto pt-3.5 text-[13.5px] ${type.linkAction}`}
                  aria-hidden
                >
                  Read article →
                </span>
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
