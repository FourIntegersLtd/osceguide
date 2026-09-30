"use client";

import { useState } from "react";
import { HiOutlinePlus, HiOutlineXMark } from "react-icons/hi2";
import { mediaItems, type MediaItem } from "@/capabilities/attempt-runner/material/sectionsByAudience";
import { b2bInputBase } from "@/capabilities/authoring/structure/b2b/theme/b2bUi";
import { Alert, PhotoUpload, type PhotoUploadResult } from "@/foundation/ui";

/**
 * Uploading to and removing from a saved station's media blocks. Absent while
 * a station is being created, when there is no version to upload to yet, and
 * on an archived version.
 */
export type MediaUploads = {
  upload: (blockId: string, files: File[]) => Promise<PhotoUploadResult>;
  remove: (url: string) => Promise<void>;
};

const input = `${b2bInputBase} py-2 text-osce-body`;

/** An item as stored: a bare URL while it has nothing else, an object once it has a caption. */
function stored(item: MediaItem): string | { url: string; caption?: string; alt?: string } {
  return item.caption || item.alt ? { url: item.url, caption: item.caption, alt: item.alt } : item.url;
}

/**
 * A media block's items: a thumbnail (or its kind) per item, a caption, and
 * remove. Images are uploaded to the bucket; audio, video and PDFs are added
 * by URL, since the upload only accepts images it can check byte by byte.
 */
export function MediaBlockEditor({
  blockId,
  label,
  required,
  value,
  readOnly,
  media,
  onChange,
}: {
  blockId: string;
  label: string;
  required: boolean;
  value: unknown;
  readOnly: boolean;
  media?: MediaUploads;
  onChange: (next: unknown) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [newUrl, setNewUrl] = useState("");
  const items = mediaItems(value);
  const write = (next: MediaItem[]) => onChange(next.map(stored));

  const remove = async (url: string) => {
    setError(null);
    if (!media) return write(items.filter((item) => item.url !== url));
    setBusy(url);
    try {
      await media.remove(url);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not remove that item.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-w-0 space-y-3 md:col-span-2">
      <p className="text-osce-body font-medium text-b2b-headline">
        {label}
        {required ? <span className="text-b2b-danger-text"> *</span> : null}
      </p>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {items.map((item, index) => (
        <div key={item.url} className="flex items-start gap-3 rounded-md border border-b2b-border bg-b2b-cream/30 p-3">
          {item.kind === "image" ? (
            // eslint-disable-next-line @next/next/no-img-element -- an author-supplied URL on any host
            <img src={item.url} alt="" className="h-20 w-20 shrink-0 rounded-md border border-b2b-border object-cover" />
          ) : (
            <span className="flex h-20 w-20 shrink-0 items-center justify-center rounded-md border border-b2b-border text-osce-caption font-semibold uppercase text-b2b-mid">
              {item.kind}
            </span>
          )}
          <div className="min-w-0 flex-1 space-y-2">
            <p className="truncate text-osce-caption text-b2b-mid" title={item.url}>
              {item.url}
            </p>
            <input
              readOnly={readOnly}
              aria-label={`Caption ${index + 1}`}
              placeholder="Caption (optional)"
              value={item.caption ?? ""}
              onChange={(event) =>
                write(items.map((other, at) => (at === index ? { ...other, caption: event.target.value } : other)))
              }
              className={input}
            />
          </div>
          {readOnly && !media ? null : (
            <button
              type="button"
              aria-label={`Remove item ${index + 1}`}
              disabled={busy !== null}
              onClick={() => void remove(item.url)}
              className="shrink-0 rounded-md p-1 text-b2b-mid hover:bg-b2b-cream hover:text-b2b-danger-text disabled:opacity-60"
            >
              <HiOutlineXMark className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>
      ))}
      {readOnly ? null : (
        <div className="flex items-center gap-2">
          <input
            aria-label={`Add a URL to ${label}`}
            placeholder="https://… (image, audio, video or PDF)"
            value={newUrl}
            onChange={(event) => setNewUrl(event.target.value)}
            className={input}
          />
          <button
            type="button"
            disabled={!newUrl.trim()}
            onClick={() => {
              write([...items, ...mediaItems(newUrl)]);
              setNewUrl("");
            }}
            className="inline-flex shrink-0 items-center gap-1 text-osce-caption font-semibold text-b2b-accent hover:underline disabled:opacity-50"
          >
            <HiOutlinePlus className="h-4 w-4" aria-hidden />
            Add
          </button>
        </div>
      )}
      {media ? (
        <PhotoUpload
          embedded
          upload={(files) => {
            setError(null);
            return media.upload(blockId, files);
          }}
          handleSuccess={() => setError(null)}
        />
      ) : null}
    </div>
  );
}
