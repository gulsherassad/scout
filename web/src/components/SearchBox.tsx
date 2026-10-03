import { useEffect, useId, useRef, useState } from "react";
import type { SearchHit } from "../api";
import { useApi } from "../lib/useApi";

const DEBOUNCE_MS = 200;
const MAX_SUGGESTIONS = 8;

/** Name search with autocomplete from /players?q=. Arrow keys move, Enter picks, Escape closes. */
export function SearchBox({ onSelect, autoFocus = false }: { onSelect: (hit: SearchHit) => void; autoFocus?: boolean }) {
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setQuery(text.trim()), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [text]);

  const { data, loading, error } = useApi<SearchHit[]>(query.length >= 2 ? `/players?q=${encodeURIComponent(query)}` : null);
  const hits = (data ?? []).slice(0, MAX_SUGGESTIONS);

  useEffect(() => setActive(0), [query]);

  const pick = (hit: SearchHit) => {
    onSelect(hit);
    setText("");
    setQuery("");
    setOpen(false);
    input.current?.blur();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, hits.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && hits[active]) {
      e.preventDefault();
      pick(hits[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const showList = open && query.length >= 2;
  return (
    <div className="searchbox">
      <label className="visually-hidden" htmlFor={`${listId}-input`}>
        Player name
      </label>
      <input
        id={`${listId}-input`}
        ref={input}
        type="search"
        placeholder="Search a player, e.g. Saka"
        value={text}
        autoFocus={autoFocus}
        autoComplete="off"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && hits[active] ? `${listId}-${hits[active].id}` : undefined}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul className="suggestions" id={listId} role="listbox">
          {loading && <li className="suggestion-note">Searching…</li>}
          {error && <li className="suggestion-note error">{error}</li>}
          {!loading && !error && hits.length === 0 && <li className="suggestion-note">No attacker in the pool matches “{query}”.</li>}
          {!loading &&
            hits.map((hit, i) => (
              <li
                key={hit.id}
                id={`${listId}-${hit.id}`}
                role="option"
                aria-selected={i === active}
                className={i === active ? "suggestion active" : "suggestion"}
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setActive(i)}
                onClick={() => pick(hit)}
              >
                <span className="suggestion-name">{hit.name}</span>
                <span className="suggestion-meta">
                  {hit.team} · {hit.position}
                </span>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
