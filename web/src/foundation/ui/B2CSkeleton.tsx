import { b2cCard } from "@/foundation/ui/productTokens";
type SkeletonCardProps = { lines?: number; className?: string };
function SkeletonCard({ lines = 3, className = "" }: SkeletonCardProps) {
  return (
    <div
      aria-busy="true"
      aria-label="Loading"
      className={[b2cCard, "space-y-3 p-5", className]
        .filter(Boolean)
        .join(" ")}
    >
      {" "}
      <div className="h-4 w-1/3 animate-pulse rounded bg-b2c-secondary" />{" "}
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={[
            "h-3 animate-pulse rounded bg-b2c-secondary",
            i === lines - 1 ? "w-2/3" : "w-full",
          ].join(" ")}
        />
      ))}{" "}
    </div>
  );
}
type SkeletonTableRowsProps = {
  count?: number;
  columns?: number;
  className?: string;
};
function SkeletonTableRows({
  count = 5,
  columns = 4,
  className = "",
}: SkeletonTableRowsProps) {
  return (
    <tbody aria-busy="true" aria-label="Loading" className={className}>
      {" "}
      {Array.from({ length: count }).map((_, rowIdx) => (
        <tr key={rowIdx} className="border-b border-b2c-border">
          {" "}
          {Array.from({ length: columns }).map((_, colIdx) => (
            <td key={colIdx} className="px-4 py-3">
              {" "}
              <div
                className={[
                  "h-3 animate-pulse rounded bg-b2c-secondary",
                  colIdx === 0 ? "w-2/3" : "w-1/2",
                ].join(" ")}
              />{" "}
            </td>
          ))}{" "}
        </tr>
      ))}{" "}
    </tbody>
  );
}
type B2CSkeletonProps = { lines?: number; className?: string };
export function B2CSkeleton({ lines = 3, className = "" }: B2CSkeletonProps) {
  return (
    <div
      aria-busy="true"
      aria-label="Loading"
      className={["space-y-2", className].filter(Boolean).join(" ")}
    >
      {" "}
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={[
            "h-3 animate-pulse rounded bg-b2c-secondary",
            i === lines - 1 ? "w-2/3" : "w-full",
          ].join(" ")}
        />
      ))}{" "}
    </div>
  );
}
B2CSkeleton.Card = SkeletonCard;
B2CSkeleton.TableRows = SkeletonTableRows;
