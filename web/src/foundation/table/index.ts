/*
 * The product's data table and its filter dropdown.
 *
 * One table for every list screen. The screen reads rows a server page at a
 * time (`useCursorPages`) and hands them over as `rows`, with `more` for the
 * "Load more" footer; or the table pages for itself through `fetchPage` when
 * the total is known. Either way no screen loads a whole list to draw a page.
 */
export {
  default as Table,
  type Column,
  type FetchPageParams,
  type FetchPageResult,
  type TableMore,
} from "@/foundation/table/Table";
export { default as Dropdown } from "@/foundation/table/Dropdown";
