"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LuCircleHelp, LuSearch, LuSparkles, LuStethoscope } from "react-icons/lu";
import Modal from "@/foundation/ui/Modal";
import { cn } from "@/foundation/ui";
import { openAthena } from "@/capabilities/help/api";
import { athenaVoiceAllowed, helpPersona } from "@/capabilities/help/helpPersona";
import { stationHref } from "@/capabilities/stations/routes";
import type { NavItem } from "@/surfaces/contract";
import { matchingSections, moveActive } from "@/surfaces/jumpTo";
import {
  MIN_QUERY_CHARS,
  NO_REMOTE,
  SEARCH_DEBOUNCE_MS,
  searchJumpTo,
  type JumpToRemote,
  type JumpToScope,
} from "@/surfaces/jumpToSearch";

/** One selectable row: where it goes, or what it does. */
interface Row {
  key: string;
  group: string;
  label: string;
  icon: NavItem["icon"];
  run: () => void;
}

/**
 * The ⌘K palette behind the toolbar's search pill: type a section's name and
 * go there, or a condition and find the stations and Help articles about it.
 * Typing is free; asking Athena is a row you choose, never a request per key.
 */
export function WorkspaceJumpTo({
  items,
  scope,
  basePath,
  athena,
  onClose,
}: {
  items: NavItem[];
  scope: JumpToScope;
  basePath: string;
  athena: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [remote, setRemote] = useState<JumpToRemote>(NO_REMOTE);
  const [searching, setSearching] = useState(false);

  const text = query.trim();
  const searchable = text.length >= MIN_QUERY_CHARS;

  useEffect(() => {
    if (!searchable) {
      setRemote(NO_REMOTE);
      setSearching(false);
      return;
    }
    setSearching(true);
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchJumpTo(text, scope, controller.signal).then((found) => {
        if (controller.signal.aborted) return;
        setRemote(found);
        setSearching(false);
      });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [text, searchable, scope]);

  const voice = athenaVoiceAllowed(usePathname());
  const rows = useMemo<Row[]>(() => {
    const go = (href: string) => () => {
      onClose();
      router.push(href);
    };
    const askAthena = (title: string) => () => {
      onClose();
      openAthena("athena", { title });
    };
    const nav: Row[] = matchingSections(items, query).map((item) => ({
      key: `nav:${item.key}`,
      group: "Pages",
      label: item.label,
      icon: item.icon,
      run: go(item.href),
    }));
    const stations: Row[] = remote.stations.map((station) => ({
      key: `station:${station.id}`,
      group: "Stations",
      label: station.title,
      icon: LuStethoscope,
      run: go(stationHref((path) => `${basePath}${path}`, station.id)),
    }));
    const articles: Row[] = (athena ? remote.articles : []).map((article) => ({
      key: `article:${article.slug}`,
      group: "Help",
      label: article.title,
      icon: LuCircleHelp,
      run: askAthena(article.title),
    }));
    const persona = helpPersona(voice);
    const ask: Row[] = athena && searchable
      ? [
          {
            key: "ask",
            group: persona.group,
            label: persona.askLabel(text),
            icon: LuSparkles,
            run: askAthena(text),
          },
        ]
      : [];
    return [...nav, ...stations, ...articles, ...ask];
  }, [items, query, remote, searchable, text, basePath, onClose, router, voice, athena]);

  return (
    <Modal
      onClose={onClose}
      title="Search"
      hideCloseButton
      initialFocusRef={inputRef}
      width={{ mobile: "92vw", desktop: "480px" }}
      bodyClassName="!p-0"
    >
      <div className="flex items-center gap-2.5 border-b border-osce-border-light px-4">
        <LuSearch className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden />
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
          }}
          onKeyDown={(event) => {
            const { key } = event;
            if (key === "ArrowDown" || key === "ArrowUp") {
              event.preventDefault();
              setActive((index) => moveActive(index, key, rows.length));
            } else if (key === "Enter") {
              event.preventDefault();
              rows[active]?.run();
            }
          }}
          placeholder="Search stations, help, pages"
          aria-label="Search stations, help, pages"
          className="h-12 min-w-0 flex-1 bg-transparent text-osce-body text-osce-ink-900 outline-none placeholder:text-osce-ink-400"
        />
      </div>
      <ul className="max-h-[50dvh] overflow-y-auto p-1.5" role="listbox" aria-label="Results">
        {rows.map((row, index) => {
          const Icon = row.icon;
          const startsGroup = index === 0 || rows[index - 1]?.group !== row.group;
          return (
            <li key={row.key} role="option" aria-selected={index === active}>
              {startsGroup ? (
                <p className="px-3 pb-1 pt-2 text-osce-caption font-medium text-b2c-text-muted">{row.group}</p>
              ) : null}
              <button
                type="button"
                onMouseEnter={() => setActive(index)}
                onClick={row.run}
                className={cn(
                  "flex h-10 w-full items-center gap-2.5 rounded-osce-md px-3 text-left text-osce-data text-osce-ink-700",
                  index === active && "bg-osce-navActive text-osce-ink-900",
                )}
              >
                {Icon ? <Icon className="h-4 w-4 shrink-0 text-osce-ink-500" /> : null}
                <span className="min-w-0 truncate">{row.label}</span>
              </button>
            </li>
          );
        })}
        {rows.length === 0 && !searching ? (
          <li className="px-3 py-6 text-center text-osce-meta text-b2c-text-muted">Nothing matches “{query}”.</li>
        ) : null}
        {searching ? <li className="px-3 py-2 text-osce-meta text-b2c-text-muted">Searching…</li> : null}
        {remote.failed ? (
          <li role="alert" className="px-3 py-2 text-osce-meta text-b2c-text-muted">
            Some results could not load. Try again.
          </li>
        ) : null}
      </ul>
    </Modal>
  );
}
