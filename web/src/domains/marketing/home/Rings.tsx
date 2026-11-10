/** Concentric outlines behind a deep-blue band. Each entry is the size, position and border colour classes of one ring. */
export function Rings({ rings }: { rings: readonly string[] }) {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {rings.map((ring) => (
        <div key={ring} className={`absolute left-1/2 -translate-x-1/2 rounded-full border ${ring}`} />
      ))}
    </div>
  );
}
