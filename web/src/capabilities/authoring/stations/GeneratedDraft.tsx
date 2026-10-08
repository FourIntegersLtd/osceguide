export function hasDraftContent(content: Record<string, unknown>): boolean {
  return Object.keys(content).length > 0;
}

export function GeneratedDraft({ content }: { content: Record<string, unknown> }) {
  return (
    <div className="rounded-osce-lg border border-border bg-white p-4">
      <p className="text-osce-body font-semibold text-ink">Generated draft</p>
      <p className="mt-1 text-osce-body text-ink-muted">
        Read this before you publish. It is not live until you save.
      </p>
      <dl className="mt-4 space-y-3">
        {Object.entries(content).map(([key, value]) => (
          <div key={key}>
            <dt className="text-osce-meta font-medium text-ink-muted">{key}</dt>
            <dd className="mt-1 whitespace-pre-wrap text-osce-body text-ink">
              {typeof value === "string" || typeof value === "number"
                ? String(value)
                : JSON.stringify(value, null, 2)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

