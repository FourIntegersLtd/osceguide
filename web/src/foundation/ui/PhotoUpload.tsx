"use client";

import { HiOutlineCloudArrowUp, HiOutlineXMark } from "react-icons/hi2";
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import Image from "next/image";
import { errorMessage as errorText } from "@/foundation/hooks";
import Alert from "@/foundation/forms/Alert";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
} from "@/foundation/ui/B2CPanelCard";
import { b2cButtonCommit, b2cLink } from "@/foundation/ui/productTokens";
import { Spinner } from "@/foundation/ui";

/** What an upload did, so partial success can be reported as partial. */
export interface PhotoUploadResult {
  uploaded: number;
  failed?: { filename: string; error: string }[];
}

interface PhotoUploadProps {
  /**
   * Send the files somewhere.
   *
   * A prop, not an endpoint spelled inside this component. The retiring
   * version posted to the old backend's `/api/upload_photos/{id}` from here,
   * which made a file picker know a route, tied it to one arm, and left it
   * untestable. The caller knows where its photos go; this knows how to pick
   * them.
   */
  upload: (files: File[]) => Promise<PhotoUploadResult>;
  handleSuccess: () => void;
  /** When true, omit outer panel card (e.g. when inside another B2CPanelCard). */
  embedded?: boolean;
}

function PhotoUpload({ upload, handleSuccess, embedded = false }: PhotoUploadProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".jpeg", ".jpg", ".png"],
    },
    maxSize: 10485760, // 10MB
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    setUploading(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const result = await upload(files);
      const failed = result.failed ?? [];
      if (result.uploaded > 0) {
        setSuccessMessage(`${result.uploaded} file(s) uploaded successfully.`);
        setFiles([]);
        handleSuccess();
      }
      if (failed.length > 0) {
        // Named, because "some failed" leaves somebody re-picking all of them.
        setErrorMessage(
          `${failed.length} file(s) failed: ${failed
            .map((f) => `${f.filename}: ${f.error}`)
            .join("; ")}`,
        );
      }
    } catch (error) {
      setErrorMessage(errorText(error));
    } finally {
      setUploading(false);
    }
  };

  const content = (
    <div className="space-y-4">
      {successMessage && (
        <Alert message={successMessage} type="success" className="mb-0" />
      )}

      {errorMessage && (
        <Alert message={errorMessage} type="error" className="mb-0" />
      )}

      <div
        {...getRootProps()}
        className={`cursor-pointer border-2 border-dashed p-6 text-center transition-colors sm:p-8 ${
          embedded ? "rounded-lg" : "rounded-md"
        } ${
          isDragActive
            ? "border-osce-accent bg-osce-accent-subtle"
            : "border-b2c-border hover:border-osce-accent"
        }`}
      >
        <input {...getInputProps()} />
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-center">
              <HiOutlineCloudArrowUp className="h-12 w-12 text-b2c-text-muted" />
            </div>
            {isDragActive ? (
              <p className="text-osce-body text-b2c-text-secondary">
                Drop the files here ...
              </p>
            ) : (
              <>
                <div className="text-osce-body text-b2c-text-secondary">
                  <span className={b2cLink}>Click to upload</span> or drag and
                  drop
                </div>
                <p className="text-osce-body text-b2c-text-muted">
                  PNG, JPG, JPEG up to 10MB each
                </p>
              </>
            )}
          </div>

          {files.length > 0 && (
            <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
              {files.map((file, index) => (
                <div key={index} className="group relative">
                  <Image
                    src={URL.createObjectURL(file)}
                    alt={`Preview ${index + 1}`}
                    width={96}
                    height={96}
                    className="h-24 w-full rounded-lg object-cover"
                  />
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="absolute right-2 top-2 rounded-full bg-osce-danger p-1 text-white opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <HiOutlineXMark className="h-4 w-4" />
                  </button>
                  <p className="mt-1 truncate text-osce-caption text-b2c-text-muted">
                    {file.name}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {files.length > 0 && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleUpload}
            disabled={uploading}
            className={`${b2cButtonCommit} inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50`}
          >
            {uploading ? (
              <>
                <Spinner size="sm" className="text-current" label="Uploading" />
                Uploading...
              </>
            ) : (
              <>
                Upload {files.length} {files.length === 1 ? "file" : "files"}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );

  if (embedded) {
    return content;
  }

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>Upload photos</B2CPanelCardHeader>
      <B2CPanelCardBody>{content}</B2CPanelCardBody>
    </B2CPanelCard>
  );
}

export default PhotoUpload;