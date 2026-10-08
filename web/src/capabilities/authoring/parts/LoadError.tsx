"use client";

/** A failed picker load, said plainly with a retry, so it never reads as an empty list. */
export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <p role="alert" className="mt-1 text-osce-caption text-danger">
      {message}{" "}
      <button type="button" onClick={onRetry} className="underline">
        Try again
      </button>
    </p>
  );
}
