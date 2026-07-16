import { useRef, useState } from "react";
import { FileText, UploadCloud, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import Card from "../ui/Card";
import Button from "../ui/Button";
import ProgressBar from "../ui/ProgressBar";
import { STATES, PLANTS, today } from "../FilterBar";
import { useDocumentUpload } from "../../hooks/useDocuments";

const fieldClasses =
  "h-10 w-full rounded-lg border border-border bg-white px-3 text-sm text-text " +
  "shadow-sm outline-none transition-colors focus:border-primary/50 focus:ring-2 focus:ring-primary/20";

const ACCEPT = ".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt";

function nowHHMM() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function UploadField({ label, children }) {
  return (
    <div className="min-w-0">
      <label className="mb-1.5 block text-xs font-medium text-muted">{label}</label>
      {children}
    </div>
  );
}

// Document upload form: State / Plant / Document Date / Document Time, then
// an explicit Choose File + Upload action (two distinct steps, unlike the
// video card's auto-upload-on-select).
export default function DocumentUpload({ onUploaded }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [meta, setMeta] = useState({
    state: STATES[0],
    plant: PLANTS[0],
    documentDate: today(),
    documentTime: nowHHMM(),
  });
  const { upload, uploading, progress, error, uploaded } = useDocumentUpload(() => {
    setFile(null);
    onUploaded?.();
  });

  const updateMeta = (field, value) => setMeta((prev) => ({ ...prev, [field]: value }));
  const openFilePicker = () => inputRef.current?.click();

  const onInputChange = (event) => {
    setFile(event.target.files?.[0] || null);
  };

  const handleUpload = () => {
    if (file) upload(file, meta);
  };

  return (
    <Card className="p-6 sm:p-8">
      <h2 className="text-base font-semibold text-text">Upload a document</h2>
      <p className="mt-1 text-sm text-muted">PDF, DOC, DOCX, XLS, XLSX, CSV, or TXT.</p>

      <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <UploadField label="State">
          <select
            className={`${fieldClasses} appearance-none`}
            value={meta.state}
            onChange={(event) => updateMeta("state", event.target.value)}
            disabled={uploading}
          >
            {STATES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </UploadField>

        <UploadField label="Plant">
          <select
            className={`${fieldClasses} appearance-none`}
            value={meta.plant}
            onChange={(event) => updateMeta("plant", event.target.value)}
            disabled={uploading}
          >
            {PLANTS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </UploadField>

        <UploadField label="Document Date">
          <input
            type="date"
            className={fieldClasses}
            value={meta.documentDate}
            onChange={(event) => updateMeta("documentDate", event.target.value)}
            disabled={uploading}
          />
        </UploadField>

        <UploadField label="Document Time">
          <input
            type="time"
            className={fieldClasses}
            value={meta.documentTime}
            onChange={(event) => updateMeta("documentTime", event.target.value)}
            disabled={uploading}
          />
        </UploadField>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={onInputChange}
      />

      <div className="mt-5 flex flex-col items-stretch gap-3 rounded-xl border border-dashed border-border bg-canvas/60 p-4 sm:flex-row sm:items-center">
        <Button variant="secondary" size="md" onClick={openFilePicker} disabled={uploading}>
          <FileText size={16} aria-hidden="true" />
          Choose File
        </Button>

        <span className="min-w-0 flex-1 truncate text-sm text-muted" title={file?.name}>
          {file ? file.name : "No file selected."}
        </span>

        <Button
          variant="primary"
          size="md"
          onClick={handleUpload}
          disabled={!file || uploading}
        >
          {uploading ? (
            <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          ) : (
            <UploadCloud size={16} aria-hidden="true" />
          )}
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
          <span className="truncate">
            <span className="font-medium">{uploaded}</span> uploaded successfully.
          </span>
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
