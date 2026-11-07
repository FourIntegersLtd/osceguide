"use client";

import { useState } from "react";
import { Button, b2bTokens as t } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { boardInput } from "@/foundation/ui/boardKit";
import {
  deleteSittingTemplate,
  listSittingTemplates,
  renameSittingTemplate,
  saveSittingTemplate,
  type SittingTemplateRead,
} from "@/domains/assess/api";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { Field, Note } from "@/domains/assess/SittingFields";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { type TemplateConfig } from "@/domains/assess/templateConfig";

/**
 * Start a schedule from a saved setup, and rename or delete the saved ones (step one).
 * Hidden without `schedule_sittings`: the templates routes are org admin.
 */
export function TemplatePicker({
  orgSlug,
  reloadKey,
  onApply,
}: {
  orgSlug: string;
  reloadKey: number;
  onApply: (config: TemplateConfig, name: string) => void;
}) {
  const w = useAssessWords();
  const { session } = useSession();
  const [version, setVersion] = useState(0);
  const state = useAsync((signal) => listSittingTemplates(orgSlug, signal), [orgSlug, reloadKey, version]);
  const [chosen, setChosen] = useState("");
  const [name, setName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "warn"; text: string } | null>(null);

  if (!can(session, "schedule_sittings")) return null;
  const templates: SittingTemplateRead[] = state.data ?? [];
  if (templates.length === 0) return null;
  const picked = templates.find((template) => template.id === chosen);

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setMessage(null);
    try {
      await work();
      setVersion((now) => now + 1);
    } catch (cause) {
      setMessage({ tone: "warn", text: assessErrorMessage(cause, w) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 border-b border-osce-border-light pb-6" data-testid="template-picker">
      <Field label={`Start from a ${w.exam} template`} htmlFor="sitting-template" hint="Fills in the stations, kind, timing and who reviews. Nothing about people or the date.">
        <select
          id="sitting-template"
          className={boardInput}
          value={chosen}
          onChange={(event) => {
            setChosen(event.target.value);
            setName(null);
            setMessage(null);
          }}
        >
          <option value="">Choose a template</option>
          {templates.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name}
            </option>
          ))}
        </select>
      </Field>
      {picked ? (
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            themeType="b2b"
            variant="secondary"
            disabled={busy}
            onClick={() => {
              onApply(picked.config, picked.name);
              setMessage({ tone: "ok", text: `Started from "${picked.name}". Change anything below.` });
            }}
          >
            Use this template
          </Button>
          {name === null ? (
            <>
              <Button themeType="b2b" variant="secondary" disabled={busy} onClick={() => setName(picked.name)}>
                Rename
              </Button>
              <Button
                themeType="b2b"
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await deleteSittingTemplate(orgSlug, picked.id);
                    setChosen("");
                    setMessage({ tone: "ok", text: `Deleted "${picked.name}".` });
                  })
                }
              >
                Delete
              </Button>
            </>
          ) : (
            <>
              <input
                aria-label="Template name"
                className={`${boardInput} max-w-[16rem]`}
                maxLength={120}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
              <Button
                themeType="b2b"
                variant="commit"
                disabled={busy || !name.trim()}
                onClick={() =>
                  void run(async () => {
                    await renameSittingTemplate(orgSlug, picked.id, name.trim());
                    setName(null);
                  })
                }
              >
                Save name
              </Button>
              <Button themeType="b2b" variant="secondary" disabled={busy} onClick={() => setName(null)}>
                Cancel
              </Button>
            </>
          )}
        </div>
      ) : null}
      {message ? (
        <Note tone={message.tone}>
          {message.text}
        </Note>
      ) : null}
    </div>
  );
}

/** Review step: keep this setup under a name. */
export function SaveAsTemplate({
  orgSlug,
  config,
  onSaved,
}: {
  orgSlug: string;
  config: TemplateConfig;
  onSaved: () => void;
}) {
  const w = useAssessWords();
  const { session } = useSession();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "warn"; text: string } | null>(null);
  if (!can(session, "schedule_sittings")) return null;

  const save = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const saved = await saveSittingTemplate(orgSlug, { name: name.trim(), config });
      setMessage({ tone: "ok", text: `Saved as "${saved.name}". Start a new ${w.sitting} from it on the first step.` });
      setName("");
      onSaved();
    } catch (cause) {
      setMessage({ tone: "warn", text: assessErrorMessage(cause, w) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3" data-testid="save-template">
      <Field label={`Save this setup as a ${w.exam} template`} htmlFor="template-name" hint="Keeps the stations, kind, timing and who reviews. Not the people or the date.">
        <div className="flex flex-wrap items-center gap-2.5">
          <input
            id="template-name"
            className={`${boardInput} max-w-[20rem]`}
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Summer OSCE setup"
          />
          <Button themeType="b2b" variant="secondary" disabled={busy || !name.trim()} onClick={() => void save()}>
            Save template
          </Button>
        </div>
      </Field>
      {message ? (
        <Note tone={message.tone}>
          {message.text}
        </Note>
      ) : (
        <p className={t.assessMeta}>Optional. You can still create the {w.sitting} without saving a template.</p>
      )}
    </div>
  );
}
