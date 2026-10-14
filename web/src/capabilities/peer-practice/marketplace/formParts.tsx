"use client";

export interface TimeOption {
  value: string;
  label: string;
}

/** Quarter-hour slots, 00:00 to 23:45, labelled the way a person reads a clock. */
export const TIME_OPTIONS: TimeOption[] = (() => {
  const out: TimeOption[] = [];
  for (let hour = 0; hour <= 23; hour += 1) {
    for (const minute of ["00", "15", "30", "45"]) {
      const suffix = hour < 12 ? "AM" : "PM";
      out.push({
        value: `${String(hour).padStart(2, "0")}:${minute}`,
        label: `${hour % 12 || 12}:${minute} ${suffix}`,
      });
    }
  }
  return out;
})();

export function TimeSlotList({
  options,
  selected,
  onSelect,
}: {
  options: TimeOption[];
  selected: string;
  onSelect: (value: string) => void;
}) {
  if (options.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-osce-body text-b2c-text-muted">
        No times left on this date. Choose a later day
      </p>
    );
  }
  return (
    <div className="py-1">
      {options.map((option) => {
        const isSelected = selected === option.value;
        return (
          <button
            key={option.value}
            type="button"
            role="option"
            aria-selected={isSelected}
            onClick={() => onSelect(option.value)}
            className={`w-full px-4 py-2.5 text-left text-osce-body outline-none transition-colors focus:ring-2 focus:ring-inset focus:ring-osce-accent/20 ${
              isSelected
                ? "bg-osce-accent font-medium text-white"
                : "text-b2c-text-secondary hover:bg-b2c-surface-muted"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
