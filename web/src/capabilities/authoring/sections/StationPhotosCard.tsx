"use client";

import { useState } from "react";
import { HiOutlineXMark } from "react-icons/hi2";
import { Alert, PhotoUpload } from "@/foundation/ui";
import { AuthoringCard } from "@/capabilities/authoring/parts/AuthoringCard";
import {
  removeStationPhoto,
  uploadStationPhotos,
  type AuthoringScope,
} from "@/capabilities/authoring/api";

/**
 * A station's images.
 *
 * The retiring admin had this and the port did not, which is why an
 * orthopaedic station — where the whole assessment is reading a radiograph —
 * could not be authored here at all.
 *
 * Ortho keeps its primary radiograph separate from the rest, because the
 * screens a candidate sees render those two fields separately. Every other
 * exam has one flat set on the doctor's information. The grouping here is the
 * same one the reader uses, so what an author sees is what a candidate gets.
 */
export function StationPhotosCard({
  scope,
  stationId,
  version,
  examCode,
  content,
  onChanged,
  readOnly,
}: {
  scope: AuthoringScope;
  stationId: string;
  version: number;
  examCode: string;
  content: Record<string, unknown>;
  onChanged: (content: Record<string, unknown>) => void;
  readOnly: boolean;
}) {
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);

  const isOrtho = examCode.trim().toLowerCase() === "ortho";
  const radiograph = typeof content.radiograph_image_url === "string" ? content.radiograph_image_url : null;
  const additional = Array.isArray(content.additional_image_urls)
    ? (content.additional_image_urls as string[])
    : [];
  const doctor = (content.doctor_information ?? {}) as Record<string, unknown>;
  const photos = Array.isArray(doctor.photos) ? (doctor.photos as string[]) : [];

  const remove = async (url: string) => {
    setRemoving(url);
    setError(null);
    try {
      const updated = await removeStationPhoto(scope, stationId, version, url);
      onChanged((updated.content ?? {}) as Record<string, unknown>);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not remove that image.");
    } finally {
      setRemoving(null);
    }
  };

  const grid = (urls: string[], label: string) =>
    urls.length === 0 ? null : (
      <div className="mt-3">
        <p className="text-osce-caption font-medium text-b2b-mid">{label}</p>
        <div className="mt-2 flex flex-wrap gap-3">
          {urls.map((url) => (
            <div key={url} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element -- an S3 URL the author just uploaded */}
              <img
                src={url}
                alt=""
                className="h-24 w-24 rounded-md border border-b2b-border object-cover"
              />
              {readOnly ? null : (
                <button
                  type="button"
                  aria-label="Remove image"
                  disabled={removing !== null}
                  onClick={() => void remove(url)}
                  className="absolute -right-2 -top-2 rounded-full border border-b2b-border bg-white p-1 text-b2b-mid shadow-sm hover:text-b2b-headline disabled:opacity-60"
                >
                  <HiOutlineXMark className="h-3.5 w-3.5" aria-hidden />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    );

  return (
    <AuthoringCard title="Photos">
      <p className="text-osce-body text-b2b-mid">
        {isOrtho
          ? "The first image on a clinical station is its radiograph; the rest are shown alongside it."
          : "Shown to the candidate with the doctor's information."}
      </p>
      {error ? (
        <Alert tone="danger" className="mt-3">
          {error}
        </Alert>
      ) : null}

      {isOrtho ? (
        <>
          {grid(radiograph ? [radiograph] : [], "Primary radiograph")}
          {grid(additional, "Additional images")}
        </>
      ) : (
        grid(photos, "Images")
      )}

      {readOnly ? (
        <p className="mt-3 text-osce-caption text-b2b-mid">
          Archived — nothing about this version may change.
        </p>
      ) : (
        <div className="mt-4">
          <PhotoUpload
            embedded
            upload={async (files) => {
              setError(null);
              const result = await uploadStationPhotos(scope, stationId, version, files);
              onChanged((result.version.content ?? {}) as Record<string, unknown>);
              return {
                uploaded: result.uploaded,
                failed: result.failed?.map((item: { filename: string; error: string }) => ({
                  filename: item.filename,
                  error: item.error,
                })),
              };
            }}
            handleSuccess={() => setError(null)}
          />
        </div>
      )}
    </AuthoringCard>
  );
}
