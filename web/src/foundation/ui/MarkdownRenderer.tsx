"use client";

import React, { useEffect, useState } from "react";
import { renderMarkdownToSafeHtml } from "@/foundation/ui/renderMarkdown";
import styles from "@/foundation/ui/markdown.module.css";

interface MarkdownRendererProps {
  content: string;
  className?: string;
  /** The same content already rendered and sanitised on the server: shown at once, and not rendered again. */
  html?: string;
}

/**
 * MarkdownRenderer - A reusable component for rendering markdown content
 *
 * The markdown-to-HTML conversion, its sanitiser and its safe fallback all live
 * in `renderMarkdownToSafeHtml` so the security-critical part is unit-tested
 * without a DOM. This component only owns state and mounting.
 *
 * Usage:
 * <MarkdownRenderer content={markdownString} />
 * <MarkdownRenderer content={markdownString} className="custom-class" />
 */
function MarkdownRenderer({ content, className = "", html }: MarkdownRendererProps) {
  const [htmlContent, setHtmlContent] = useState(html ?? "");

  useEffect(() => {
    if (html !== undefined) return;
    let cancelled = false;
    renderMarkdownToSafeHtml(content).then((html) => {
      if (!cancelled) setHtmlContent(html);
    });
    return () => {
      cancelled = true;
    };
  }, [content, html]);

  return (
    <div
      className={`${styles.markdownContent} ${className}`}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}

export default MarkdownRenderer;
