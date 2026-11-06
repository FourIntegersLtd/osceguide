"use client";

import { PopupMenu } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import type { SchemeTabId } from "@/capabilities/authoring/rubrics/schemeModel";

export type AddChoice = "domain" | "competency" | "notes" | Extract<SchemeTabId, "scale" | "pass" | "feedback">;

const ITEMS: readonly { id: AddChoice; label: string }[] = [
  { id: "domain", label: "Domain" },
  { id: "competency", label: "Competency" },
  { id: "notes", label: "Notes" },
  { id: "scale", label: "Scale" },
  { id: "pass", label: "Pass rule" },
  { id: "feedback", label: "Feedback" },
];

/** One Add button: domains, competencies and notes are added here; the rest jump to their tab. */
export function AddMenu({ canAddCompetency, onChoose }: { canAddCompetency: boolean; onChoose: (choice: AddChoice) => void }) {
  return (
    <PopupMenu
      className="mt-1 w-56"
      trigger={({ open, toggle }) => (
        <AuthoringButton variant="secondary" size="sm" aria-haspopup="menu" aria-expanded={open} onClick={toggle}>
          Add
        </AuthoringButton>
      )}
    >
      {(close) =>
        ITEMS.map((item) => {
          const disabled = item.id === "competency" && !canAddCompetency;
          return (
            <li key={item.id} role="none">
              <button
                type="button"
                role="menuitem"
                disabled={disabled}
                className="flex min-h-9 w-full flex-col items-start justify-center rounded px-3 text-left text-osce-body text-ink hover:bg-osce-canvas disabled:text-ink-subtle"
                onClick={() => {
                  close();
                  onChoose(item.id);
                }}
              >
                {item.label}
                {disabled ? <span className="text-osce-caption">Pick a domain first.</span> : null}
              </button>
            </li>
          );
        })
      }
    </PopupMenu>
  );
}
