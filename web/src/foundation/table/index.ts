/*
 * The product's data table and its filter dropdown.
 *
 * One table, paged from the server through `fetchPage`, so every list screen
 * sorts, filters and pages the same way and none of them re-implements it.
 */
export {
  default as Table,
  type FetchPageParams,
  type FetchPageResult,
} from "@/foundation/table/Table";
export { default as Dropdown } from "@/foundation/table/Dropdown";
