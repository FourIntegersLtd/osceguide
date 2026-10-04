"use client";

import { useMemo, useState } from "react";
import { Alert, B2CPageHeader, Button, productTokens, Panel } from "@/foundation/ui";
import {
  B2CSegmentedTabs,
  type B2CSegmentedTabItem,
} from "@/foundation/ui/B2CSegmentedTabs";
import { useSession } from "@/foundation/session";
import { sendSiteMessage } from "@/capabilities/help/api";
import { ProductFeedbackForm } from "@/capabilities/help/ProductFeedbackForm";
import { B2CHero } from "@/foundation/ui/B2CHero";

const { b2cFieldLabel, b2cSettingsFieldInput } = productTokens;

const fieldClass = b2cSettingsFieldInput;

type MessagesTab = "contact" | "feedback";

/*
 * A port of the retiring client's `/messages` screen — "Contact & Feedback",
 * two tabs. The Contact tab writes to the team and the Feedback tab is the
 * product-feedback form. Both post to `POST /site/messages` now, which files
 * them apart by `kind`; the old client posted both to `/api/create_message`.
 *
 * One adaptation: the old screen widened from `max-w-2xl` to `max-w-full`
 * when the help dock beside it was expanded, read off a context the shell
 * owned. The shells here keep that state to themselves, and every sibling
 * port settled on the fixed width, so this does too.
 */

function ContactForm() {
  const { session } = useSession();
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccessMessage(null);
    setErrorMessage(null);
    try {
      await sendSiteMessage({
        kind: "contact",
        name: session?.user.name || null,
        email: session?.user.email || null,
        subject,
        body: message,
        source: "messages-screen",
      });
      setSubject("");
      setMessage("");
      setSuccessMessage(
        "Message successfully sent! We aim to respond within the next 12 hours.",
      );
    } catch {
      setErrorMessage(
        "An error occurred while sending your message. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <B2CHero eyebrow="Contact" title="Send a message to the team">
        If you are reporting a problem with a station, flag it in the station and tell us which one. We
        aim to reply within 12 hours.
      </B2CHero>

      <form onSubmit={handleSubmit}>
        <Panel title="Your message">
          <div className="space-y-4">
            <div>
              <label htmlFor="subject" className={b2cFieldLabel}>
                Subject
              </label>
              <input
                type="text"
                id="subject"
                placeholder="Enter message subject"
                className={`mt-1.5 ${fieldClass}`}
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="message" className={b2cFieldLabel}>
                Message
              </label>
              <textarea
                id="message"
                placeholder="Write your message here..."
                className={`mt-1.5 ${fieldClass} min-h-[10rem] resize-y`}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
              />
            </div>
            <Button type="submit" isLoading={loading}>
              Send message
            </Button>
            {successMessage ? <Alert tone="success">{successMessage}</Alert> : null}
            {errorMessage ? <Alert tone="danger">{errorMessage}</Alert> : null}
          </div>
        </Panel>
      </form>
    </div>
  );
}

export function Messages() {
  const [tab, setTab] = useState<MessagesTab>("contact");

  const tabItems = useMemo(
    (): B2CSegmentedTabItem<MessagesTab>[] => [
      { id: "contact", label: "Contact" },
      { id: "feedback", label: "Feedback" },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      <B2CPageHeader title="Contact & Feedback" />
      <div className="max-w-3xl space-y-6">
        <B2CSegmentedTabs
          items={tabItems}
          value={tab}
          onChange={setTab}
          aria-label="Contact and feedback"
        />

        {tab === "contact" ? (
          <ContactForm />
        ) : (
          <ProductFeedbackForm
            source="contact"
            showIntro={false}
            cardTitle="We'd love your feedback"
          />
        )}
      </div>
    </div>
  );
}

export default Messages;
