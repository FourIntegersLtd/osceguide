"use client";
import { B2BModal } from "@/capabilities/authoring/structure/b2b/components/ui/B2BModal";
import { formsOrderForKind, type TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { B2BButton } from "@/capabilities/authoring/structure/b2b/components/ui/B2BButton";
export function StationBlockTypesInfoModal({
  kind = "station",
  open,
  onClose,
}: {
  kind?: TemplateKind;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <B2BModal
      open={open}
      onClose={onClose}
      title="Field types for stations & templates"
      size="lg"
    >
      {" "}
      <B2BModal.Body>
        {" "}
        <p className="text-osce-body text-osce-ink-500 leading-relaxed">
          {" "}
          These are the building blocks for station and feedback templates.
          Pick the type that best matches what you want trainees or examiners
          to fill in.{" "}
        </p>{" "}
        <ul className="mt-5 space-y-5">
          {" "}
          {formsOrderForKind(kind).map((m) => {
            const Icon = m.icon;
            return (
              <li
                key={m.type}
                className="flex gap-3 border-b border-osce-border pb-5 last:border-0 last:pb-0"
              >
                {" "}
                <span className="mt-0.5 shrink-0 text-osce-ink-500">
                  {" "}
                  <Icon className="h-6 w-6" aria-hidden />{" "}
                </span>{" "}
                <div className="min-w-0">
                  {" "}
                  <p className="font-semibold text-osce-ink-700">
                    {m.formsLabel}
                  </p>{" "}
                  <p className="mt-1 text-osce-body text-osce-ink-500 leading-relaxed">
                    {m.description}
                  </p>{" "}
                </div>{" "}
              </li>
            );
          })}{" "}
        </ul>{" "}
      </B2BModal.Body>{" "}
      <B2BModal.Footer>
        {" "}
        <B2BButton variant="secondary" onClick={onClose}>
          {" "}
          Close{" "}
        </B2BButton>{" "}
      </B2BModal.Footer>{" "}
    </B2BModal>
  );
}
