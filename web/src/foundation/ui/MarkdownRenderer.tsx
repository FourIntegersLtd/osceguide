"use client";

import React, { useEffect, useState } from "react";
import { remark } from "remark";
import remarkRehype from "remark-rehype";
import rehypeRaw from "rehype-raw";
import rehypeStringify from "rehype-stringify";
import styles from "@/foundation/ui/markdown.module.css";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * MarkdownRenderer - A reusable component for rendering markdown content
 * 
 * Usage:
 * <MarkdownRenderer content={markdownString} />
 * <MarkdownRenderer content={markdownString} className="custom-class" />
 */
function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const [htmlContent, setHtmlContent] = useState("");

  useEffect(() => {
    const processMarkdown = async () => {
      try {
        const result = await remark()
          .use(remarkRehype, { allowDangerousHtml: true })
          .use(rehypeRaw)
          .use(rehypeStringify)
          .process(content);
        setHtmlContent(String(result));
      } catch (error) {
        console.error("Error processing markdown:", error);
        setHtmlContent(content); // Fallback to raw content
      }
    };

    if (content) {
      processMarkdown();
    } else {
      setHtmlContent("");
    }
  }, [content]);

  return (
    <div
      className={`${styles.markdownContent} ${className}`}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}

export default MarkdownRenderer;

