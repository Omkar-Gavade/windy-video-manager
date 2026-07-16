import {
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
import Card from "./ui/Card";
import Button from "./ui/Button";

const DASH = "—";

// Format an ISO / date-only value as e.g. "15 Jul 2026"; fall back gracefully.
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

// Format an ISO timestamp as e.g. "15 Jul 2026 10:02 AM".
function formatDateTime(value) {
  if (!value) return DASH;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const datePart = formatDate(value);
  const timePart = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
  return `${datePart} ${timePart}`;
}

// Format a bare "HH:MM:SS" time string as e.g. "09:31:55 AM".
function formatRecordingTime(value) {
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

// One labelled metadata row with a leading icon.
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

// Single recording card. Presentation restructured in Phase 3; behaviour
// (preview / download) is unchanged.
export default function VideoCard({ video, onPreview, onDownload, downloading = false }) {
  const {
    filename,
    upload_date: uploadDate,
    size,
    s3_path: s3Path,
    state,
    plant,
    recording_date: recordingDate,
    recording_time: recordingTime,
  } = video;

  return (
    <Card hover className="flex flex-col p-5">
      {/* Filename — medium, monospace, wraps. */}
      <p
        className="break-all font-mono text-sm font-medium text-text"
        title={filename}
      >
        {filename}
      </p>

      {/* Plant — largest, bold. */}
      <p className="mt-2 flex items-center gap-1.5 text-base font-bold text-text">
        <Building2 size={16} className="shrink-0 text-primary" aria-hidden="true" />
        {plant || DASH}
      </p>

      {/* Metadata rows. */}
      <div className="mt-3 space-y-1.5 border-t border-border pt-3">
        <Row icon={MapPin} label="State" value={state || DASH} />
        <Row icon={CalendarDays} label="Recorded" value={formatDate(recordingDate)} />
        <Row icon={Clock} label="Recording Time" value={formatRecordingTime(recordingTime)} />
        <Row icon={Clock3} label="Uploaded" value={formatDateTime(uploadDate)} />
        <Row icon={HardDrive} label="Size" value={size} />
      </div>

      {/* S3 path — small monospace, wraps. */}
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

      {/* Actions. */}
      <div className="mt-5 flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          className="flex-1"
          onClick={() => onPreview(video)}
        >
          <Play size={14} aria-hidden="true" />
          Preview
        </Button>
        <Button
          variant="primary"
          size="sm"
          className="flex-1"
          onClick={() => onDownload(video)}
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
