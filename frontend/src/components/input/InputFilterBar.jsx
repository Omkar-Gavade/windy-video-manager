import { useState } from "react";
import { MapPin, Building2, Calendar, Layers, Film, RefreshCw } from "lucide-react";
import Card from "../ui/Card";
import { today } from "../FilterBar";
import { useInputOptions } from "../../hooks/useInputOptions";

export const CATEGORIES = [
  "Site Details",
  "Enercast Data",
  "Metered Data",
  "WP",
  "Fetch Manifest",
];
export const WP_TYPES = ["Images", "Videos"];

const control =
  "h-11 w-full rounded-xl border border-border bg-white pl-10 pr-3 text-sm text-text " +
  "shadow-sm outline-none transition-colors focus:border-primary/50 focus:ring-2 focus:ring-primary/20";

function Field({ label, icon: Icon, children }) {
  return (
    <div className="min-w-0">
      <label className="mb-1.5 block text-xs font-medium text-muted">{label}</label>
      <div className="relative">
        <Icon size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
        {children}
      </div>
    </div>
  );
}

// Filter bar for the Inputs page. Holds its own selection; emits on Load only.
export default function InputFilterBar({ onLoad, loading = false }) {
  const { states, plants, state, plant, setState, setPlant, loadingStates, loadingPlants } =
    useInputOptions();
  const [inputDate, setInputDate] = useState(today);
  const [category, setCategory] = useState("");
  const [wpType, setWpType] = useState("");

  const isWP = category === "WP";
  const noStates = !loadingStates && states.length === 0;
  const noPlants = !loadingPlants && plants.length === 0;

  // Search is mandatory: State, Plant and Input Date must all be chosen.
  const canLoad = Boolean(state && plant && inputDate);
  const handleLoad = () => {
    if (!canLoad) return;
    onLoad({
      state,
      plant,
      inputDate,
      category: category || undefined,
      wpType: isWP ? wpType || undefined : undefined,
    });
  };

  return (
    <Card className="p-4 sm:p-5">
      <div className={`grid grid-cols-1 gap-4 sm:grid-cols-2 lg:items-end ${isWP ? "lg:grid-cols-[1fr_1fr_1fr_1fr_1fr_auto]" : "lg:grid-cols-[1fr_1fr_1fr_1fr_auto]"}`}>
        <Field label="State" icon={MapPin}>
          <select
            className={`${control} appearance-none`}
            value={state}
            onChange={(e) => setState(e.target.value)}
            disabled={loadingStates || noStates}
          >
            {loadingStates ? (
              <option value="">Loading…</option>
            ) : noStates ? (
              <option value="">No states available</option>
            ) : (
              states.map((o) => <option key={o} value={o}>{o}</option>)
            )}
          </select>
        </Field>

        <Field label="Plant" icon={Building2}>
          <select
            className={`${control} appearance-none`}
            value={plant}
            onChange={(e) => setPlant(e.target.value)}
            disabled={loadingPlants || noPlants}
          >
            {loadingPlants ? (
              <option value="">Loading…</option>
            ) : noPlants ? (
              <option value="">No plants available</option>
            ) : (
              plants.map((o) => <option key={o} value={o}>{o}</option>)
            )}
          </select>
        </Field>

        <Field label="Input Date" icon={Calendar}>
          <input type="date" className={control} value={inputDate} onChange={(e) => setInputDate(e.target.value)} />
        </Field>

        <Field label="Category" icon={Layers}>
          <select
            className={`${control} appearance-none`}
            value={category}
            onChange={(e) => { setCategory(e.target.value); setWpType(""); }}
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </Field>

        {isWP ? (
          <Field label="WP Type" icon={Film}>
            <select className={`${control} appearance-none`} value={wpType} onChange={(e) => setWpType(e.target.value)}>
              <option value="">All</option>
              {WP_TYPES.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
        ) : null}

        <button
          type="button"
          onClick={handleLoad}
          disabled={loading || !canLoad}
          className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-success px-6 text-sm font-semibold text-white shadow-soft transition-all hover:bg-success/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-success/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} aria-hidden="true" />
          Load Inputs
        </button>
      </div>

      {!canLoad ? (
        <p className="mt-3 text-xs text-muted">
          Please select State, Plant and Input Date.
        </p>
      ) : null}
    </Card>
  );
}
