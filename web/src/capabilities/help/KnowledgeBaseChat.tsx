"use client";
import { useEffect, useRef, useState } from "react";
import { MdMenuBook } from "react-icons/md";
import { HiOutlineChevronRight } from "react-icons/hi2";
import { BsInfoCircleFill } from "react-icons/bs";
import { B2CPanelCard, B2CPanelCardHeader, Button } from "@/foundation/ui";
import MarkdownRenderer from "@/foundation/ui/MarkdownRenderer";
import mdStyles from "@/foundation/ui/markdown.module.css";
import { helpType } from "@/foundation/ui/helpType";
import { errorMessage } from "@/foundation/hooks";
import { askKnowledge } from "./api";
const helpPanelFooter = "shrink-0 border-t border-osce-border-light bg-osce-surface p-3 pb-[max(0.75rem,env(safe-area-inset-bottom,0px))] sm:p-4 lg:pb-4";

export function KnowledgeBaseChat({
  examCode,
}: {
  examCode?: string;
}) {
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (preset?: string) => {
    const text = (preset ?? input).trim();
    if (!text || loading) return;
    setInput("");
    const userMessage = { role: "user" as const, content: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    try {
      const nextMessages = [...messages, userMessage];
      const data = await askKnowledge(nextMessages, examCode);
      const reply =
        (data?.reply || "").trim() ||
        "I could not generate a response. Please try again.";
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err: unknown) {
      const errorMsg = errorMessage(err instanceof Error ? err : new Error(String(err)));
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Search failed: ${errorMsg}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const suggestions = [
    "What are the red flags for chest pain?",
    "How do I manage hypertension in clinic?",
    "Summarise the approach to shortness of breath",
  ];

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden text-osce-body">
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4"
      >
        {messages.length === 0 ? (
          <div className="pb-2">
            <div className="mb-4 flex flex-col items-center text-center">
              <span className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-osce-accent-muted text-osce-accent">
                <MdMenuBook className="h-5 w-5" aria-hidden />
              </span>
              <h3 className={helpType.title}>
                Knowledge base
              </h3>
              <p className={`mt-1 max-w-[18rem] ${helpType.support}`}>
                Ask about conditions, management, and clinical content from our
                summaries.
              </p>
            </div>

            <h3 className={helpType.title}>
              Try asking
            </h3>
            <p className={`mt-0.5 ${helpType.support}`}>
              Tap a suggestion or type your own question below
            </p>

            <B2CPanelCard className="mt-4">
              <B2CPanelCardHeader>Suggestions</B2CPanelCardHeader>
              <ul>
                {suggestions.map((q) => (
                  <li
                    key={q}
                    className="border-b border-osce-border-light last:border-b-0"
                  >
                    <button
                      type="button"
                      onClick={() => void handleSend(q)}
                      disabled={loading}
                      className="flex w-full items-start gap-3 px-4 py-3.5 text-left transition hover:bg-osce-canvas disabled:opacity-60"
                    >
                      <span className={`min-w-0 flex-1 ${helpType.rowTitle}`}>
                        {q}
                      </span>
                      <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-osce-ink-400" />
                    </button>
                  </li>
                ))}
              </ul>
            </B2CPanelCard>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex shrink-0 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[90%] rounded-xl px-3.5 py-2.5 ${
                    m.role === "user"
                      ? `bg-osce-accent-muted ${helpType.prose} text-osce-accent-hover`
                      : "border border-osce-border-light bg-osce-surface text-osce-ink-800 shadow-sm"
                  }`}
                >
                  {m.role === "assistant" ? (
                    <MarkdownRenderer
                      content={m.content}
                      className={mdStyles.helpCompact}
                    />
                  ) : (
                    <p className="whitespace-pre-wrap break-words">{m.content}</p>
                  )}
                </div>
              </div>
            ))}
            {loading ? (
              <div className="flex justify-start shrink-0">
                <div className="rounded-xl border border-osce-border-light bg-osce-surface px-3.5 py-2.5 text-osce-meta leading-relaxed text-osce-ink-500 shadow-sm">
                  Searching knowledge base…
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>

      <div className={helpPanelFooter}>
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            placeholder="Ask a question…"
            rows={2}
            className="min-h-[2.75rem] max-h-32 w-full resize-y rounded-xl border border-osce-border px-3 py-2.5 text-osce-body leading-relaxed text-osce-ink-900 outline-none placeholder:text-osce-ink-400 focus:border-osce-accent-light focus:ring-2 focus:ring-osce-accent-muted disabled:opacity-60"
            disabled={loading}
          />
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={() => void handleSend()}
            disabled={loading}
            className="shrink-0"
          >
            Send
          </Button>
        </div>
        <p className="mt-2 flex items-start justify-center gap-1.5 text-center text-osce-meta leading-relaxed text-osce-ink-500">
          <BsInfoCircleFill className="mt-0.5 h-3 w-3 shrink-0 text-osce-ink-400" />
          AI-generated. Do not rely on this for clinical decisions.
        </p>
      </div>
    </div>
  );
}

