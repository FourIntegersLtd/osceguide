"use client";

import { HiOutlineArrowPath, HiOutlineExclamationCircle } from "react-icons/hi2";

/*
 * How a marketplace list looks while it loads and when it fails.
 *
 * The retiring screen drew both inline, smaller than the app's default spinner
 * panel, and the three tabs shared them. They go to `AsyncBoundary`'s
 * `loading` and `failure` slots, so the retry still comes from the boundary.
 */

export function ListLoading() {
  return (
    <div className="flex items-center justify-center py-12">
      <HiOutlineArrowPath className="h-6 w-6 animate-spin text-osce-accent" />
    </div>
  );
}

export function ListLoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <HiOutlineExclamationCircle className="mb-3 h-8 w-8 text-osce-danger" />
      <p className="text-osce-body text-b2c-text-secondary">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-osce-body font-medium text-osce-accent hover:text-osce-accent-hover"
      >
        Try again
      </button>
    </div>
  );
}
