import {
  FileText,
  Building2,
  MapPin,
  CalendarDays,
  Clock,
  Clock3,
  HardDrive,
  Folder,
  Play,
  Download,
  Loader2,
} from "lucide-react";
import Card from "../ui/Card";
import Button from "../ui/Button";

const DASH = "—";

function formatDate(value) {
  if (!value) return DASH;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatDateTime(value) {
  if (!value) return DASH;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const timePart = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
  return `${formatDate(value)} ${timePart}`;
}

function formatTime(value) {
  if (!value) return DASH;
  const [h, m, s] = value.split(":").map(Number);
  if ([h, m, s].some(Number.isNaN)) return value;
  const asDate = new Date(2000, 0, 1, h, m, s);
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  }).format(asDate);
}

function Row({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted">
      <Icon size={13} className="shrink-0" aria-hidden="true" />
      <span className="text-muted">{label}</span>
      <span className="ml-auto truncate font-medium text-text" title={value}>
        {value}
      </span>
    </div>
  );
}

// Single document card. Same visual language as VideoCard (Card, Row,
// typography scale) — the Documents page is part of the same application.
export default function DocumentCard({ document: doc, onPreview, onDownload, downloading = false }) {
  const {
    filename,
    upload_date: uploadDate,
    size,
    s3_path: s3Path,
    state,
    plant,
    document_date: documentDate,
    document_time: documentTime,
  } = doc;

  return (
    <Card hover className="flex flex-col p-5">
      {/* Document name — medium, monospace, wraps. */}
      <p className="flex items-start gap-1.5 break-all font-mono text-sm font-medium text-text" title={filename}>
        <FileText size={14} className="mt-0.5 shrink-0 text-muted" aria-hidden="true" />
        {filename}
      </p>

      {/* Plant — largest, bold. */}
      <p className="mt-2 flex items-center gap-1.5 text-base font-bold text-text">
        <Building2 size={16} className="shrink-0 text-primary" aria-hidden="true" />
        {plant || DASH}
      </p>

      <div className="mt-3 space-y-1.5 border-t border-border pt-3">
        <Row icon={MapPin} label="State" value={state || DASH} />
        <Row icon={CalendarDays} label="Document Date" value={formatDate(documentDate)} />
        <Row icon={Clock} label="Document Time" value={formatTime(documentTime)} />
        <Row icon={Clock3} label="Uploaded" value={formatDateTime(uploadDate)} />
        <Row icon={HardDrive} label="Size" value={size} />
      </div>

      <div className="mt-3">
        <p className="mb-1 flex items-center gap-1 text-xs font-medium text-muted">
          <Folder size={12} aria-hidden="true" />
          S3 path
        </p>
        <p
          className="break-all rounded-lg border border-border bg-canvas px-2.5 py-1.5 font-mono text-[11px] leading-relaxed text-muted"
          title={s3Path}
        >
          {s3Path}
        </p>
      </div>

      <div className="mt-5 flex gap-2">
        <Button variant="secondary" size="sm" className="flex-1" onClick={() => onPreview(doc)}>
          <Play size={14} aria-hidden="true" />
          Preview
        </Button>
        <Button
          variant="primary"
          size="sm"
          className="flex-1"
          onClick={() => onDownload(doc)}
          disabled={downloading}
        >
          {downloading ? (
            <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          ) : (
            <Download size={14} aria-hidden="true" />
          )}
          {downloading ? "Preparing…" : "Download"}
        </Button>
      </div>
    </Card>
  );
}
