import { useRef, useState } from "react";
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import Card from "./ui/Card";
import Button from "./ui/Button";
import ProgressBar from "./ui/ProgressBar";
import { today } from "./FilterBar";
import { useUpload } from "../hooks/useUpload";
import { useVideoOptions } from "../hooks/useVideoOptions";

const fieldClasses =
  "h-10 w-full rounded-lg border border-border bg-white px-3 text-sm text-text " +
  "shadow-sm outline-none transition-colors focus:border-primary/50 focus:ring-2 focus:ring-primary/20";

const nowHHMM = () => {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

// Labelled metadata field for the upload form.
function UploadField({ label, children }) {
  return (
    <div className="min-w-0">
      <label className="mb-1.5 block text-xs font-medium text-muted">{label}</label>
      {children}
    </div>
  );
}

// Upload surface: state/plant/date/time metadata, then drag-and-drop / browse.
// States/Plants are discovered dynamically from S3 (no hardcoded values). The
// metadata is submitted with the file so the backend builds the deterministic
// key + JSON sidecar. `onUploaded` refreshes the library after success.
export default function UploadCard({ onUploaded }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const { states, plants, state, plant, setState, setPlant, loadingStates, loadingPlants } =
    useVideoOptions();
  const [recordingDate, setRecordingDate] = useState(today());
  const [recordingTime, setRecordingTime] = useState(nowHHMM());
  const { upload, uploading, progress, error, uploaded } = useUpload(onUploaded);

  const openFilePicker = () => inputRef.current?.click();

  const handleFiles = (files) => {
    const file = files?.[0];
    if (file) upload(file, { state, plant, recordingDate, recordingTime });
  };

  const onInputChange = (event) => {
    handleFiles(event.target.files);
    event.target.value = ""; // allow re-selecting the same file
  };

  const onDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    if (uploading) return;
    handleFiles(event.dataTransfer.files);
  };

  const onDragOver = (event) => {
    event.preventDefault();
    if (!uploading) setDragging(true);
  };

  const dropzoneClasses = [
    "rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
    dragging
      ? "border-primary bg-primary/5"
      : "border-border bg-canvas/60 hover:border-primary/40 hover:bg-canvas",
  ].join(" ");

  return (
    <Card className="p-6 sm:p-8">
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={onInputChange}
      />

      {/* Upload metadata — submitted with the file to build the structured key. */}
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <UploadField label="State">
          <select
            className={`${fieldClasses} appearance-none`}
            value={state}
            onChange={(event) => setState(event.target.value)}
            disabled={uploading || loadingStates || states.length === 0}
          >
            {loadingStates ? (
              <option value="">Loading…</option>
            ) : states.length === 0 ? (
              <option value="">No states found</option>
            ) : (
              states.map((o) => <option key={o} value={o}>{o}</option>)
            )}
          </select>
        </UploadField>

        <UploadField label="Plant">
          <select
            className={`${fieldClasses} appearance-none`}
            value={plant}
            onChange={(event) => setPlant(event.target.value)}
            disabled={uploading || loadingPlants || plants.length === 0}
          >
            {loadingPlants ? (
              <option value="">Loading…</option>
            ) : plants.length === 0 ? (
              <option value="">No plants found</option>
            ) : (
              plants.map((o) => <option key={o} value={o}>{o}</option>)
            )}
          </select>
        </UploadField>

        <UploadField label="Recording Date">
          <input
            type="date"
            className={fieldClasses}
            value={recordingDate}
            onChange={(event) => setRecordingDate(event.target.value)}
            disabled={uploading}
          />
        </UploadField>

        <UploadField label="Recording Time">
          <input
            type="time"
            className={fieldClasses}
            value={recordingTime}
            onChange={(event) => setRecordingTime(event.target.value)}
            disabled={uploading}
          />
        </UploadField>
      </div>

      <div
        className={dropzoneClasses}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={() => setDragging(false)}
      >
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          {uploading ? (
            <Loader2 size={26} className="animate-spin" aria-hidden="true" />
          ) : (
            <UploadCloud size={26} aria-hidden="true" />
          )}
        </span>

        <h2 className="mt-5 text-base font-semibold text-text">
          {uploading ? "Uploading…" : "Upload a video"}
        </h2>
        <p className="mx-auto mt-1.5 max-w-sm text-sm text-muted">
          Drag and drop a video file here, or browse to select one from your
          computer.
        </p>

        <div className="mt-6">
          <Button
            variant="primary"
            size="md"
            onClick={openFilePicker}
            disabled={uploading}
          >
            <UploadCloud size={16} aria-hidden="true" />
            Browse files
          </Button>
        </div>
      </div>

      {/* Progress — shown while a file is in flight. */}
      {uploading ? (
        <div className="mt-5">
          <div className="mb-1.5 flex items-center justify-between text-xs text-muted">
            <span>Uploading to S3</span>
            <span>{progress}%</span>
          </div>
          <ProgressBar value={progress} />
        </div>
      ) : null}

      {/* Success feedback. */}
      {!uploading && uploaded ? (
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2.5 text-sm text-text">
          <CheckCircle2 size={16} className="text-success" aria-hidden="true" />
          <span className="truncate">
            <span className="font-medium">{uploaded}</span> uploaded successfully.
          </span>
        </div>
      ) : null}

      {/* Error feedback. */}
      {!uploading && error ? (
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
          <AlertCircle size={16} className="text-red-500" aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}
    </Card>
  );
}
