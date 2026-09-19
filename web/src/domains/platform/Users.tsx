"use client";

import { useCallback, useState } from "react";
import { LuShieldCheck } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card, ConfirmModal, Input, PageHeader } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { searchUsers, setPlatformAdmin, type User } from "@/domains/platform/api";
import { LoadMore, Row, RowList, Section } from "@/domains/platform/chrome";
import { formatDay } from "@/domains/platform/support";

/**
 * Finding an account, for the people who answer "I cannot sign in".
 *
 * Two of the retiring console's screens in one. `/platform/users` was a search
 * and `/platform/team` was the list of people who run this console; there is
 * no listing of platform administrators on `platform-api`, and `UserSummary`
 * does not say whether an account is one — so the team screen has no read to
 * build on and the grant lives here, on the person it is about.
 *
 * That means this screen cannot show who is already an administrator, and it
 * does not pretend to: granting and revoking are two explicit acts rather than
 * a toggle whose position would be a guess. `docs/port-gaps.md` names the
 * field that would fix it.
 *
 * The old user detail — memberships, revoking portal access per organisation,
 * resetting a password — has no endpoints here either, so a row is a row.
 */
export function Users() {
  const [term, setTerm] = useState("");
  const [query, setQuery] = useState("");
  const [extra, setExtra] = useState<{ query: string; rows: User[]; cursor: string | null }>({
    query: "",
    rows: [],
    cursor: null,
  });
  const [paging, setPaging] = useState(false);
  const [pageError, setPageError] = useState<Error | null>(null);
  /** What this session has just changed, so a row can say so. `null` is unknown. */
  const [changed, setChanged] = useState<Record<string, boolean>>({});

  const state = useAsync((signal) => searchUsers({ q: query }, signal), [query]);

  const appended = extra.query === query ? extra.rows : [];
  const cursor = extra.query === query && extra.rows.length > 0
    ? extra.cursor
    : (state.data?.next_cursor ?? null);

  const loadMore = useCallback(async () => {
    if (!cursor) return;
    setPaging(true);
    setPageError(null);
    try {
      const page = await searchUsers({ q: query, cursor });
      setExtra((current) => ({
        query,
        rows: [...(current.query === query ? current.rows : []), ...page.items],
        cursor: page.next_cursor ?? null,
      }));
    } catch (cause) {
      setPageError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setPaging(false);
    }
  }, [cursor, query]);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="Users" description="Everyone with an account, across every organisation." />

      <Card padding="md">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            setExtra({ query: term.trim(), rows: [], cursor: null });
            setQuery(term.trim());
          }}
        >
          <Input
            className="sm:flex-1"
            type="search"
            label="Email"
            placeholder="Part of an email address"
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            hint="Leave it empty to list everybody, newest first."
          />
          <Button type="submit">Search</Button>
        </form>
      </Card>

      <Section title="Accounts">
        <AsyncBoundary
          state={state}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: "No accounts match",
            description: "Try part of the address rather than the whole of it.",
          }}
        >
          {(page) => (
            <div className="flex flex-col gap-3">
              <RowList>
                {[...page.items, ...appended].map((user) => (
                  <UserRow
                    key={user.id}
                    user={user}
                    justChanged={changed[user.id]}
                    onChanged={(isAdmin) =>
                      setChanged((current) => ({ ...current, [user.id]: isAdmin }))
                    }
                  />
                ))}
              </RowList>
              {pageError ? <Alert tone="danger">{errorMessage(pageError)}</Alert> : null}
              <LoadMore cursor={cursor} busy={paging} onLoad={() => void loadMore()} />
            </div>
          )}
        </AsyncBoundary>
      </Section>
    </div>
  );
}

/**
 * One account, and the one thing this console can do to it.
 *
 * Both acts sit behind a disclosure rather than on the row. Granting this is
 * the most dangerous button in the product — it hands somebody every
 * organisation — and a list of eighteen people should not carry eighteen of
 * them a click away from a mis-tap.
 *
 * `justChanged` is what this session did, not what is stored — there is
 * nothing to read. It is deliberately not persisted or assumed on load: a
 * badge that survived a refresh would be a claim the backend never made.
 */
function UserRow({
  user,
  justChanged,
  onChanged,
}: {
  user: User;
  justChanged: boolean | undefined;
  onChanged: (isAdmin: boolean) => void;
}) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirm = useCallback(async () => {
    if (pending === null) return;
    setBusy(true);
    setError(null);
    try {
      await setPlatformAdmin(user.id, pending);
      onChanged(pending);
      toast.success(
        pending
          ? `${user.email} can now open this console`
          : `${user.email} can no longer open this console`,
        "They must sign in again for it to take effect.",
      );
      setPending(null);
      setOpen(false);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [pending, user.id, user.email, onChanged, toast]);

  return (
    <>
      <Row className="flex-col items-stretch sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{user.email}</p>
            <p className="truncate text-xs text-ink-subtle">
              {user.name || "No name"} · joined {formatDay(user.created_at)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {justChanged !== undefined ? (
              <Badge tone={justChanged ? "success" : "neutral"}>
                <LuShieldCheck className="mr-1 h-3 w-3" aria-hidden />
                {justChanged ? "Granted" : "Revoked"}
              </Badge>
            ) : null}
            <Button
              variant="ghost"
              size="sm"
              aria-expanded={open}
              onClick={() => setOpen((current) => !current)}
            >
              {open ? "Close" : "Console access"}
            </Button>
          </div>
        </div>

        {open ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3 sm:mt-0 sm:w-full">
            <p className="min-w-0 flex-1 text-xs text-ink-subtle">
              Whether {user.email} already has this is not something the API answers, so both acts
              are offered and neither is shown as current.
            </p>
            <Button variant="secondary" size="sm" onClick={() => setPending(true)}>
              Grant
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setPending(false)}>
              Revoke
            </Button>
          </div>
        ) : null}
      </Row>

      <ConfirmModal
        isOpen={pending !== null}
        onCancel={() => {
          setPending(null);
          setError(null);
        }}
        onConfirm={() => void confirm()}
        isLoading={busy}
        error={error}
        tone={pending === false ? "danger" : "default"}
        title={pending ? "Grant the staff console?" : "Revoke the staff console?"}
        confirmText={pending ? "Grant" : "Revoke"}
        message={
          pending
            ? `${user.email} will be able to see and change every organisation on the platform.`
            : `${user.email} will lose this console. Their memberships of individual organisations are untouched.`
        }
      />
    </>
  );
}
