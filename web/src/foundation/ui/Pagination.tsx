"use client";

import React from "react";
import { b2cButtonSecondarySm } from "@/foundation/ui/productTokens";
interface PaginationProps {
  currentPage: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (itemsPerPage: number) => void;
  /** When true, same First/Prev/Next/Last UI but Last disabled, Next follows hasMore */ cursorMode?: boolean;
  /** When cursorMode, Next enabled only when hasMore */ hasMore?: boolean;
  /** When true, totalItems is the real total from API; use offset style and cap pages at ceil(total/perPage) */ knownTotal?: boolean;
}
function Pagination({
  currentPage,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
  cursorMode = false,
  hasMore = false,
  knownTotal: knownTotalFromParent = undefined,
}: PaginationProps) {
  const endOfRange =
    (currentPage - 1) * itemsPerPage + Math.min(itemsPerPage, totalItems);
  // Use parent's knownTotal when provided so last page (e.g. 16 of 773 items) stays "Page 16 of 16"; otherwise infer
  const hasKnownTotal =
    knownTotalFromParent === true
      ? true
      : knownTotalFromParent === false
        ? false
        : totalItems > endOfRange ||
          (totalItems > 0 && totalItems <= itemsPerPage);
  const totalPages = hasKnownTotal
    ? Math.max(1, Math.ceil(totalItems / itemsPerPage))
    : cursorMode
      ? Math.max(1, hasMore ? currentPage + 1 : currentPage)
      : Math.max(1, Math.ceil(totalItems / itemsPerPage));
  const canGoNext = hasKnownTotal
    ? currentPage < totalPages
    : cursorMode
      ? hasMore
      : currentPage < totalPages;
  const showOffsetStyle = !cursorMode || hasKnownTotal;
  return (
    <div className="flex flex-col sm:flex-row justify-end items-center gap-4 pb-20">
      {" "}
      {/* Page Size Selector */}{" "}
      <div className="flex items-center gap-2 w-full sm:w-auto justify-center">
        {" "}
        <span className="text-b2c-text-secondary text-osce-body">
          Page Size:
        </span>{" "}
        <select
          value={itemsPerPage}
          onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
          className="border rounded px-2 py-1 text-osce-body"
        >
          {" "}
          <option value="10">10</option> <option value="20">20</option>{" "}
          <option value="50">50</option> <option value="100">100</option>{" "}
          <option value="200">200</option>{" "}
        </select>{" "}
      </div>{" "}
      {/* Page Information and Navigation */}{" "}
      <div className="flex flex-col sm:flex-row items-center gap-2 w-full sm:w-auto">
        {" "}
        <span className="text-b2c-text-secondary text-osce-body text-center">
          {" "}
          {showOffsetStyle
            ? `${(currentPage - 1) * itemsPerPage + 1} to ${Math.min(currentPage * itemsPerPage, totalItems)} of ${totalItems}`
            : canGoNext
              ? `${(currentPage - 1) * itemsPerPage + 1} to ${endOfRange} (more)`
              : `${(currentPage - 1) * itemsPerPage + 1} to ${endOfRange}`}{" "}
        </span>{" "}
        <div className="flex gap-1">
          {" "}
          <button
            onClick={() => onPageChange(1)}
            disabled={currentPage === 1}
            className={b2cButtonSecondarySm}
            aria-label="First page"
          >
            {" "}
            ⟪{" "}
          </button>{" "}
          <button
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className={b2cButtonSecondarySm}
            aria-label="Previous page"
          >
            {" "}
            ⟨{" "}
          </button>{" "}
          <span className="px-2 py-1 text-osce-body">
            {" "}
            {showOffsetStyle
              ? `Page ${currentPage} of ${totalPages}`
              : canGoNext
                ? `Page ${currentPage} (next →)`
                : `Page ${currentPage}`}{" "}
          </span>{" "}
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={!canGoNext}
            className={b2cButtonSecondarySm}
            aria-label="Next page"
          >
            {" "}
            ⟩{" "}
          </button>{" "}
          <button
            onClick={() => onPageChange(totalPages)}
            disabled={!showOffsetStyle || currentPage === totalPages}
            className={b2cButtonSecondarySm}
            aria-label="Last page"
          >
            {" "}
            ⟫{" "}
          </button>{" "}
        </div>{" "}
      </div>{" "}
    </div>
  );
}
export default Pagination;