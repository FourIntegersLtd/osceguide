"use client";

import { SUPPORT_REPLY_HOURS } from "@/foundation/config/copyNumbers";
import { useMemo, useState } from "react";
import { useToast } from "@/foundation/hooks";
import { Alert, B2CPageHeader, Button, Input, Select, productTokens, Panel } from "@/foundation/ui";
import {
  B2CSegmentedTabs,
  type B2CSegmentedTabItem,
} from "@/foundation/ui/B2CSegmentedTabs";
import { useSession } from "@/foundation/session";
import { sendSiteMessage } from "@/capabilities/help/api";
import { ProductFeedbackForm } from "@/capabilities/help/ProductFeedbackForm";
import { CONTACT_SUBJECTS, contactSubjectText, type ContactSubject } from "@/capabilities/help/contactSubject";

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
  const toast = useToast();
  const [choice, setChoice] = useState<ContactSubject | "">("");
  const [otherSubject, setOtherSubject] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    try {
      await sendSiteMessage({
        kind: "contact",
        name: session?.user.name || null,
        email: session?.user.email || null,
        subject: contactSubjectText(choice, otherSubject),
        body: message,
        source: "messages-screen",
      });
      setChoice("");
      setOtherSubject("");
      setMessage("");
      toast.success(
        "Message sent",
        `We aim to respond within the next ${SUPPORT_REPLY_HOURS} hours.`,
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
      <p className="text-osce-body text-b2c-text-secondary">
        Tell us about a problem, ask a question or request information. To report a faulty station, use
        Flag station inside the station; use this form for anything else. We reply within{" "}
        {SUPPORT_REPLY_HOURS} hours.
      </p>

      <form onSubmit={handleSubmit}>
        <Panel title="Your message">
          <div className="space-y-4">
            <div>
              <label htmlFor="subject" className={b2cFieldLabel}>
                Subject
              </label>
              <Select
                id="subject"
                className="mt-1.5"
                value={choice}
                onChange={(e) => setChoice(e.target.value as ContactSubject | "")}
                required
              >
                <option value="" disabled>
                  Choose a subject
                </option>
                {CONTACT_SUBJECTS.map((subject) => (
                  <option key={subject.value} value={subject.value}>
                    {subject.label}
                  </option>
                ))}
              </Select>
              {choice === "other" ? (
                <Input
                  aria-label="Your subject"
                  className="mt-2"
                  placeholder="Enter message subject"
                  value={otherSubject}
                  onChange={(e) => setOtherSubject(e.target.value)}
                  required
                />
              ) : null}
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
      <div className="space-y-6">
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
