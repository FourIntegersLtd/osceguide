"use client";

import { useCallback, useMemo, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { HiOutlineCloudArrowUp } from "react-icons/hi2";
import { Alert, Select, Spinner, TextLink } from "@/foundation/ui";
import { errorMessage, useAsync, useMeEvents } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  copyStationTemplate,
  draftStationFromImport,
  listStationImports,
  listStationTemplates,
  publishStationTemplate,
  uploadStationImport,
  type StationImport,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import { AuthoringExamSelect } from "@/capabilities/authoring/parts/AuthoringExamSelect";
import { matchesExamFilter } from "@/capabilities/authoring/parts/examCatalogFilter";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { latestOf } from "@/capabilities/authoring/sections/versions";
import { stationTemplateEditPath } from "@/capabilities/authoring/templates/paths";

/**
 * Bring a station written elsewhere into the library from a PDF or Word file.
 *
 * Two steps with a person between them. The first file drafts a template and
 * stops, so the author reviews and publishes the shape before anything is
 * built on it. That file, and every later file uploaded against the published
 * template, is then copied into it as a draft station.
 *
 * An organisation starts on the standard simulation template instead, so its
 * briefings all land in one shape and the first step is skipped. It fills its
 * own copy, which the first upload makes if the organisation has none.
 *
 * Both steps are background jobs. The dialog lists the scope's recent imports
 * and re-reads them when `station_import.updated` arrives, so closing it or
 * leaving the page loses nothing: the rows are on the server.
 */

// The same limit the backend enforces, checked here so a large file is refused
// before it is sent.
const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
};
// How many past imports the dialog shows. The backend returns up to fifty.
const VISIBLE_IMPORTS = 8;
// A template drafted by an import is always that template's first version.
const DRAFTED_TEMPLATE_VERSION = 1;
// The picker value meaning "draft a new template from this file".
const NEW_TEMPLATE = "";
// The picker value meaning "copy the standard template into my organisation,
// then fill the copy".
const COPY_STANDARD = "copy-standard";
// The seeded platform template every organisation starts from, and the title
// its copy keeps. A renamed copy is no longer recognised, and is still listed.
const STANDARD_TEMPLATE_TITLE = "Simulation scenario (ASPiH)";

export function ImportStationDialog({
  open,
  onClose,
  onChanged,
}: {
  open: boolean;
  onClose: () => void;
  /** Called when an import creates a template or a station, so the list behind can re-read. */
  onChanged: () => void;
}) {
  // Mounted only while open, so nothing is fetched or listened for otherwise.
  if (!open) return null;
  return <ImportStationDialogBody onClose={onClose} onChanged={onChanged} />;
}

function ImportStationDialogBody({
  onClose,
  onChanged,
}: {
  onClose: () => void;
  onChanged: () => void;
}) {
  const scope = useAuthoringScope();
  const [examCode, setExamCode] = useState("");
  // Null until the author picks, so the default can follow the templates once they load.
  const [pickedTemplate, setPickedTemplate] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const imports = useAsync((signal) => listStationImports(scope, signal), [scope.base]);
  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);
  const reloadImports = imports.reload;
  const reloadTemplates = templates.reload;

  // The jobs publish this event when an import changes status. A `resync` is
  // the hook's own "you may have missed something", sent when the tab comes
  // back into view, which is also when a template may have been published in
  // another tab.
  useMeEvents(
    ["station_import.updated"],
    useCallback(
      (event) => {
        reloadImports();
        reloadTemplates();
        if (event.name !== "resync") onChanged();
      },
      [reloadImports, reloadTemplates, onChanged],
    ),
  );

  // The platform's standard template, which an organisation fills only through its own copy.
  const standard = useMemo(
    () => (scope.kind === "org" ? platformStandard(templates.data?.items ?? []) : null),
    [templates.data, scope.kind],
  );
  const publishedTemplates = useMemo(
    () =>
      publishedTemplateOptions(templates.data?.items ?? [], examCode).filter(
        (option) => option.templateId !== standard?.id,
      ),
    [templates.data, examCode, standard],
  );
  // Found by what it was copied from, not by a title the organisation may have changed.
  const ownStandard = publishedTemplates.find(
    (option) => standard !== null && option.copiedFromId === standard.id,
  );
  const standardToCopy =
    standard !== null && !(templates.data?.items ?? []).some((template) => template.copied_from_id === standard.id)
      ? standard
      : null;
  const offersCopy = standardToCopy !== null && ownStandard === undefined;
  // A pick that is no longer offered (the exam changed, or the standard was
  // copied in another tab) gives way to the default.
  const offered = [NEW_TEMPLATE, ...(offersCopy ? [COPY_STANDARD] : []), ...publishedTemplates.map((o) => o.versionId)];
  const templateVersionId =
    pickedTemplate !== null && offered.includes(pickedTemplate)
      ? pickedTemplate
      : (ownStandard?.versionId ?? (offersCopy ? COPY_STANDARD : NEW_TEMPLATE));
  const publishedVersionIds = useMemo(
    () => new Set(publishedTemplateOptions(templates.data?.items ?? [], "").map((option) => option.versionId)),
    [templates.data],
  );

  // A new template is drafted from one file. Several files only make sense
  // against a template that already exists.
  const allowsSeveralFiles = templateVersionId !== NEW_TEMPLATE;
  const chosenFiles = allowsSeveralFiles ? files : files.slice(0, 1);

  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length === 0) return;
      setError(null);
      setFiles(accepted);
    },
    [],
  );
  const onDropRejected = useCallback((rejections: FileRejection[]) => {
    setError(rejectionMessage(rejections[0]?.errors[0]?.code));
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_BYTES,
    multiple: allowsSeveralFiles,
  });

  async function upload() {
    setUploading(true);
    setError(null);
    // One request per file, in turn: each is rate limited and buys a model
    // call, and a refusal of one file should not stop the rest.
    const refused: string[] = [];
    let versionId = templateVersionId;
    if (versionId === COPY_STANDARD && standardToCopy !== null) {
      try {
        const copy = await copyStationTemplate(scope, standardToCopy.id);
        versionId = latestOf(copy.versions).published?.id ?? NEW_TEMPLATE;
        setPickedTemplate(versionId);
        reloadTemplates();
        onChanged();
      } catch (cause) {
        setUploading(false);
        setError(errorMessage(cause));
        return;
      }
    }
    for (const file of chosenFiles) {
      try {
        await uploadStationImport(scope, { file, examCode, templateVersionId: versionId || null });
      } catch (cause) {
        refused.push(`${file.name}: ${errorMessage(cause)}`);
      }
    }
    setFiles([]);
    setUploading(false);
    reloadImports();
    if (refused.length > 0) setError(refused.join(" "));
  }

  const recent = (imports.data?.imports ?? []).slice(0, VISIBLE_IMPORTS);

  return (
    <AuthoringDialog
      open
      title="Import from PDF or Word"
      lead="Upload a station you have already written. We copy its words into a template. Nothing is added or rewritten."
      error={error}
      busy={uploading}
      commitLabel={chosenFiles.length > 1 ? `Upload ${chosenFiles.length} files` : "Upload"}
      busyLabel="Uploading…"
      // Which template a file goes to is decided by the templates, so nothing is
      // sent before they have loaded.
      commitDisabled={chosenFiles.length === 0 || examCode === "" || templates.data === null}
      onClose={onClose}
      onCommit={() => void upload()}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-osce-meta font-medium text-ink-muted" htmlFor="import-exam">
          Exam
          <AuthoringExamSelect
            id="import-exam"
            value={examCode}
            onChange={(code) => {
              setExamCode(code);
              // A template picked for another exam no longer applies.
              setPickedTemplate(null);
            }}
            required
          />
        </label>
        <label className="block text-osce-meta font-medium text-ink-muted" htmlFor="import-template">
          Template
          <Select
            id="import-template"
            className="mt-1"
            value={templateVersionId}
            onChange={(event) => {
              setPickedTemplate(event.target.value);
            }}
          >
            {offersCopy && standardToCopy !== null ? (
              <option value={COPY_STANDARD}>{STANDARD_TEMPLATE_TITLE} (standard)</option>
            ) : null}
            {publishedTemplates.map((option) => (
              <option key={option.versionId} value={option.versionId}>
                {option.title}
              </option>
            ))}
            <option value={NEW_TEMPLATE}>Make a new template from this file</option>
          </Select>
        </label>
      </div>

      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-panel border border-dashed border-border p-6 text-center transition-colors ${
          isDragActive ? "bg-osce-accent-muted" : "bg-osce-surface hover:bg-osce-surface-alt"
        }`}
      >
        <input {...getInputProps()} />
        <HiOutlineCloudArrowUp className="mx-auto h-7 w-7 text-ink-subtle" aria-hidden />
        <p className="mt-2 text-osce-body font-medium text-ink">
          {chosenFiles.length > 0
            ? chosenFiles.map((file) => file.name).join(", ")
            : isDragActive
              ? "Drop the file here"
              : allowsSeveralFiles
                ? "Drop your station files, or click to choose"
                : "Drop one station file, or click to choose"}
        </p>
        <p className="mt-1 text-osce-meta text-ink-subtle">
          PDF or Word (.docx), one station per file, up to 10MB each.
          {allowsSeveralFiles
            ? " You can add several files at once."
            : " Your first file sets the template. After you publish it you can add the rest together."}
        </p>
      </div>

      {imports.error ? <Alert tone="danger">{imports.error.message}</Alert> : null}
      {recent.length > 0 ? (
        <section aria-label="Recent imports" className="space-y-2">
          <h3 className="text-osce-meta font-semibold uppercase tracking-wide text-ink-subtle">
            Recent imports
          </h3>
          <ul className="divide-y divide-border rounded-panel border border-border">
            {recent.map((stationImport) => (
              <ImportRow
                key={stationImport.id}
                stationImport={stationImport}
                templatePublished={
                  stationImport.template_version_id != null &&
                  publishedVersionIds.has(stationImport.template_version_id)
                }
                onStarted={reloadImports}
              />
            ))}
          </ul>
        </section>
      ) : null}
    </AuthoringDialog>
  );
}

/** One import: its file, how far it has got, and the next thing its author can do. */
function ImportRow({
  stationImport,
  templatePublished,
  onStarted,
}: {
  stationImport: StationImport;
  templatePublished: boolean;
  onStarted: () => void;
}) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const { status, template_id: templateId } = stationImport;
  const drafting = status === "drafting_template" || status === "drafting_station";
  // A failed import that already has a template failed at the station step, and
  // the backend lets that step be tried again.
  const canCreateStation =
    templateId != null && (status === "template_ready" || status === "failed");

  async function createStation() {
    if (templateId == null) return;
    setBusy(true);
    setFailure(null);
    try {
      // A station can only be built on a published template, so publishing is
      // part of this button when the author has not already done it.
      if (!templatePublished) await publishStationTemplate(scope, templateId);
      await draftStationFromImport(scope, stationImport.id);
      onStarted();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="space-y-2 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="min-w-0 truncate text-osce-body font-medium text-ink">
          {stationImport.original_filename}
        </p>
        <p className="flex items-center gap-2 text-osce-meta text-ink-subtle" role="status">
          {drafting ? <Spinner label="Working" /> : null}
          {statusLine(status)}
        </p>
      </div>

      {status === "failed" && stationImport.error ? (
        <Alert tone="danger">{stationImport.error}</Alert>
      ) : null}
      {failure ? <Alert tone="danger">{failure}</Alert> : null}

      {status === "completed" ? <CheckNotes stationImport={stationImport} /> : null}

      {canCreateStation ? (
        <div className="flex flex-wrap items-center gap-3">
          {status === "template_ready" && !templatePublished ? (
            <TextLink
              variant="muted"
              className="text-osce-meta"
              target="_blank"
              href={stationTemplateEditPath(hrefFor, templateId, DRAFTED_TEMPLATE_VERSION)}
            >
              Review the template
            </TextLink>
          ) : null}
          <AuthoringButton
            variant="secondary"
            size="sm"
            disabled={busy}
            onClick={() => void createStation()}
          >
            {busy
              ? "Starting…"
              : templatePublished
                ? "Create the station"
                : "Publish template and create the station"}
          </AuthoringButton>
        </div>
      ) : null}
    </li>
  );
}

/** What the author should check on a finished draft: parts left empty and parts not word for word. */
function CheckNotes({ stationImport }: { stationImport: StationImport }) {
  const empty = stationImport.empty_block_ids ?? [];
  const reworded = stationImport.reworded_block_ids ?? [];
  if (empty.length === 0 && reworded.length === 0) {
    return (
      <p className="text-osce-meta text-ink-subtle">
        Every part of the template was filled word for word from your file.
      </p>
    );
  }
  return (
    <div className="space-y-1 text-osce-meta text-ink-muted">
      {empty.length > 0 ? (
        <p>
          Left empty because your file had nothing for them: {empty.map(readableBlockId).join(", ")}.
        </p>
      ) : null}
      {reworded.length > 0 ? (
        <p>
          Check these against your file, the wording may differ:{" "}
          {reworded.map(readableBlockId).join(", ")}.
        </p>
      ) : null}
    </div>
  );
}

type TemplateOption = {
  templateId: string;
  versionId: string;
  title: string;
  ownerKind: string;
  copiedFromId: string | null;
};

/** Published templates the picker offers, narrowed to one exam when one is chosen. */
function publishedTemplateOptions(
  templates: readonly StationTemplate[],
  examCode: string,
): TemplateOption[] {
  const options: TemplateOption[] = [];
  for (const template of templates) {
    const { published } = latestOf(template.versions);
    if (!published) continue;
    if (!matchesExamFilter(template.exam_code, examCode, { includeUnscoped: true })) continue;
    options.push({
      templateId: template.id,
      versionId: published.id,
      title: template.title,
      ownerKind: template.owner_kind,
      copiedFromId: template.copied_from_id ?? null,
    });
  }
  return options;
}

/** The platform's published standard template. Its title is the key the seed writes it under. */
function platformStandard(templates: readonly StationTemplate[]): StationTemplate | null {
  return (
    templates.find(
      (template) =>
        template.owner_kind === "platform" &&
        template.title === STANDARD_TEMPLATE_TITLE &&
        latestOf(template.versions).published !== null,
    ) ?? null
  );
}

function statusLine(status: string): string {
  switch (status) {
    case "drafting_template":
      return "Reading the file and drafting a template. This takes about a minute.";
    case "template_ready":
      return "Template drafted. Review it, then create the station.";
    case "drafting_station":
      return "Copying the file into the template. This takes about a minute.";
    case "completed":
      return "Draft station created. It is in your Stations list.";
    case "failed":
      return "Could not be imported";
    default:
      return status;
  }
}

/** A block id is a slug of its label, so spaces read better than separators. */
function readableBlockId(blockId: string): string {
  return blockId.replace(/[_-]+/g, " ");
}

function rejectionMessage(code: string | undefined): string {
  if (code === "file-too-large") return "That file is larger than 10MB.";
  if (code === "file-invalid-type") return "Only PDF and Word (.docx) files can be imported.";
  if (code === "too-many-files") return "A new template is made from one file. Choose one.";
  return "We could not take that file.";
}
