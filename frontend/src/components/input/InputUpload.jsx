import { useEffect, useRef, useState } from "react";
import { FileText, UploadCloud, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import Card from "../ui/Card";
import Button from "../ui/Button";
import ProgressBar from "../ui/ProgressBar";
import { today } from "../FilterBar";
import { CATEGORIES, WP_TYPES } from "./InputFilterBar";
import { useInputUpload } from "../../hooks/useInputs";
import { useInputOptions } from "../../hooks/useInputOptions";

const SITE_DETAILS_FILES = ["site_details.json", "site_configuration.json", "metadata.json"];

const field =
  "h-10 w-full rounded-lg border border-border bg-white px-3 text-sm text-text " +
  "shadow-sm outline-none transition-colors focus:border-primary/50 focus:ring-2 focus:ring-primary/20";

// Live wall-clock as "HH:MM:SS AM/PM".
function formatClock(date) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  }).format(date);
}

function UploadField({ label, children }) {
  return (
    <div className="min-w-0">
      <label className="mb-1.5 block text-xs font-medium text-muted">{label}</label>
      {children}
    </div>
  );
}

// Input upload form: category-driven destination, explicit Choose File + Upload,
// and a live Input Time clock captured at the moment of upload.
export default function InputUpload({ onUploaded }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const { states, plants, state, plant, setState, setPlant, loadingStates, loadingPlants } =
    useInputOptions();
  const [category, setCategory] = useState(CATEGORIES[0]); // "Site Details"
  const [subCategory, setSubCategory] = useState(SITE_DETAILS_FILES[0]);
  const [wpType, setWpType] = useState(WP_TYPES[0]);
  const [inputDate, setInputDate] = useState(today());
  const [clock, setClock] = useState(() => formatClock(new Date()));

  const { upload, uploading, progress, error, uploaded } = useInputUpload(() => {
    setFile(null);
    onUploaded?.();
  });

  // Live time — ticks every second, no re-render of anything heavy.
  useEffect(() => {
    const id = setInterval(() => setClock(formatClock(new Date())), 1000);
    return () => clearInterval(id);
  }, []);

  const isSiteDetails = category === "Site Details";
  const isWP = category === "WP";
  const showDate = !isSiteDetails;

  const openFilePicker = () => inputRef.current?.click();

  const handleUpload = () => {
    if (!file) return;
    upload(file, {
      state,
      plant,
      category,
      inputTime: clock, // capture the exact displayed value
      inputDate: showDate ? inputDate : undefined,
      wpType: isWP ? wpType : undefined,
      subCategory: isSiteDetails ? subCategory : undefined,
    });
  };

  const acceptFor = isWP && wpType === "Images"
    ? "image/*"
    : isWP && wpType === "Videos"
      ? "video/*"
      : isSiteDetails || category === "Fetch Manifest"
        ? ".json"
        : ".csv,.txt,.json,.xls,.xlsx,.pdf,.dat";

  return (
    <Card className="p-6 sm:p-8">
      <h2 className="text-base font-semibold text-text">Upload an input</h2>
      <p className="mt-1 text-sm text-muted">
        Choose a category and file. Filenames are preserved
        {category === "Fetch Manifest" ? " (stored as fetch_manifest.json)" : ""}.
      </p>

      <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <UploadField label="State">
          <select
            className={`${field} appearance-none`}
            value={state}
            onChange={(e) => setState(e.target.value)}
            disabled={uploading || loadingStates || states.length === 0}
          >
            {loadingStates ? (
              <option value="">Loading…</option>
            ) : states.length === 0 ? (
              <option value="">No states available</option>
            ) : (
              states.map((o) => <option key={o} value={o}>{o}</option>)
            )}
          </select>
        </UploadField>

        <UploadField label="Plant">
          <select
            className={`${field} appearance-none`}
            value={plant}
            onChange={(e) => setPlant(e.target.value)}
            disabled={uploading || loadingPlants || plants.length === 0}
          >
            {loadingPlants ? (
              <option value="">Loading…</option>
            ) : plants.length === 0 ? (
              <option value="">No plants available</option>
            ) : (
              plants.map((o) => <option key={o} value={o}>{o}</option>)
            )}
          </select>
        </UploadField>

        <UploadField label="Input Category">
          <select className={`${field} appearance-none`} value={category} onChange={(e) => setCategory(e.target.value)} disabled={uploading}>
            {CATEGORIES.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </UploadField>

        {isSiteDetails ? (
          <UploadField label="Site Details File">
            <select className={`${field} appearance-none`} value={subCategory} onChange={(e) => setSubCategory(e.target.value)} disabled={uploading}>
              {SITE_DETAILS_FILES.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </UploadField>
        ) : null}

        {isWP ? (
          <UploadField label="WP Type">
            <select className={`${field} appearance-none`} value={wpType} onChange={(e) => setWpType(e.target.value)} disabled={uploading}>
              {WP_TYPES.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </UploadField>
        ) : null}

        {showDate ? (
          <UploadField label="Input Date">
            <input type="date" className={field} value={inputDate} onChange={(e) => setInputDate(e.target.value)} disabled={uploading} />
          </UploadField>
        ) : null}

        <UploadField label="Input Time (live)">
          <input
            type="text"
            className={`${field} font-mono tabular-nums text-muted`}
            value={clock}
            readOnly
            aria-live="off"
          />
        </UploadField>
      </div>

      <input ref={inputRef} type="file" accept={acceptFor} className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />

      <div className="mt-5 flex flex-col items-stretch gap-3 rounded-xl border border-dashed border-border bg-canvas/60 p-4 sm:flex-row sm:items-center">
        <Button variant="secondary" size="md" onClick={openFilePicker} disabled={uploading}>
          <FileText size={16} aria-hidden="true" />
          Choose File
        </Button>
        <span className="min-w-0 flex-1 truncate text-sm text-muted" title={file?.name}>
          {file ? file.name : "No file selected."}
        </span>
        <Button variant="primary" size="md" onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <UploadCloud size={16} aria-hidden="true" />}
          Upload
        </Button>
      </div>

      {uploading ? (
        <div className="mt-5">
          <div className="mb-1.5 flex items-center justify-between text-xs text-muted">
            <span>Uploading to S3</span>
            <span>{progress}%</span>
          </div>
          <ProgressBar value={progress} />
        </div>
      ) : null}

      {!uploading && uploaded ? (
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2.5 text-sm text-text">
          <CheckCircle2 size={16} className="text-success" aria-hidden="true" />
          <span className="truncate"><span className="font-medium">{uploaded}</span> uploaded successfully.</span>
        </div>
      ) : null}

      {!uploading && error ? (
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
          <AlertCircle size={16} className="text-red-500" aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}
    </Card>
  );
}
