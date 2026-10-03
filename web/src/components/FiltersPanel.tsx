import { useEffect, useState } from "react";
import type { Filters } from "../lib/format";

const DEBOUNCE_MS = 350;

/** Market filters. Number fields update after a short pause; the checkbox at once. */
export function FiltersPanel({ value, onChange }: { value: Filters; onChange: (f: Filters) => void }) {
  const [draft, setDraft] = useState({
    maxAge: value.maxAge?.toString() ?? "",
    maxValue: value.maxValue?.toString() ?? "",
    contractBefore: value.contractBefore?.toString() ?? "",
  });

  useEffect(() => {
    const t = setTimeout(() => {
      const num = (s: string) => (s.trim() === "" ? undefined : Number(s));
      const next = { ...value, maxAge: num(draft.maxAge), maxValue: num(draft.maxValue), contractBefore: num(draft.contractBefore) };
      if (next.maxAge !== value.maxAge || next.maxValue !== value.maxValue || next.contractBefore !== value.contractBefore) {
        onChange(next);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [draft]); // eslint-disable-line react-hooks/exhaustive-deps

  const field = (key: keyof typeof draft, label: string, props: React.InputHTMLAttributes<HTMLInputElement>) => (
    <label className="filter">
      <span>{label}</span>
      <input type="number" inputMode="numeric" value={draft[key]} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} {...props} />
    </label>
  );

  const anySet = draft.maxAge || draft.maxValue || draft.contractBefore || value.includeInactive;
  return (
    <form className="filters" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
      {field("maxAge", "Max age", { min: 15, max: 45, placeholder: "any" })}
      {field("maxValue", "Max value (€m)", { min: 0, step: 0.5, placeholder: "any" })}
      {field("contractBefore", "Contract ends before", { min: 2025, max: 2040, placeholder: "any year" })}
      <label className="filter filter-check">
        <input type="checkbox" checked={value.includeInactive} onChange={(e) => onChange({ ...value, includeInactive: e.target.checked })} />
        <span>Include inactive</span>
      </label>
      {anySet && (
        <button
          type="button"
          className="btn-ghost"
          onClick={() => {
            setDraft({ maxAge: "", maxValue: "", contractBefore: "" });
            onChange({ includeInactive: false });
          }}
        >
          Clear
        </button>
      )}
    </form>
  );
}
