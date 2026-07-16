import { useState } from "react";
import { MapPin, Building2, Calendar, RefreshCw } from "lucide-react";
import Card from "./ui/Card";

// Selection options, shared with the upload form.
export const STATES = ["Madhya Pradesh", "Maharashtra", "Gujarat", "Rajasthan"];
export const PLANTS = ["SIRMOUR", "SATNA", "REWA", "KATNI"];

export const today = () => new Date().toISOString().slice(0, 10);

const controlClasses =
  "h-11 w-full rounded-xl border border-border bg-white pl-10 pr-3 text-sm text-text " +
  "shadow-sm outline-none transition-colors focus:border-primary/50 focus:ring-2 focus:ring-primary/20";

// Small labelled field with a leading icon. Keeps the row visually consistent.
function Field({ label, icon: Icon, children }) {
  return (
    <div className="min-w-0">
      <label className="mb-1.5 block text-xs font-medium text-muted">{label}</label>
      <div className="relative">
        <Icon
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          aria-hidden="true"
        />
        {children}
      </div>
    </div>
  );
}

// Premium horizontal filter card: State, Plant, a date field, Load button.
// Holds its own selection; fetching only happens when the button is clicked,
// which emits the current filters to the parent (never while typing).
// `dateLabel`/`buttonLabel` let this be reused as-is for the Documents page
// (defaults preserve the exact video-page behaviour: "Recording Date" /
// "Load Videos").
export default function FilterBar({
  onLoad,
  loading = false,
  dateLabel = "Recording Date",
  buttonLabel = "Load Videos",
}) {
  const [state, setState] = useState(STATES[0]);
  const [plant, setPlant] = useState(PLANTS[0]);
  const [recordingDate, setRecordingDate] = useState(today);

  const handleLoad = () => onLoad({ state, plant, recordingDate });

  return (
    <Card className="p-4 sm:p-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end">
        <Field label="State" icon={MapPin}>
          <select
            className={`${controlClasses} appearance-none`}
            value={state}
            onChange={(event) => setState(event.target.value)}
          >
            {STATES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Plant" icon={Building2}>
          <select
            className={`${controlClasses} appearance-none`}
            value={plant}
            onChange={(event) => setPlant(event.target.value)}
          >
            {PLANTS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field label={dateLabel} icon={Calendar}>
          <input
            type="date"
            className={controlClasses}
            value={recordingDate}
            onChange={(event) => setRecordingDate(event.target.value)}
          />
        </Field>

        <button
          type="button"
          onClick={handleLoad}
          disabled={loading}
          className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-success px-6 text-sm font-semibold text-white shadow-soft transition-all hover:bg-success/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-success/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
        >
          <RefreshCw
            size={16}
            className={loading ? "animate-spin" : ""}
            aria-hidden="true"
          />
          {buttonLabel}
        </button>
      </div>
    </Card>
  );
}
