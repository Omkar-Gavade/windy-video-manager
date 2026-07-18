import {
  FileText, Building2, MapPin, CalendarDays, Clock, Clock3,
  HardDrive, Folder, Layers, Film, Play, Download, Loader2,
} from "lucide-react";
import Card from "../ui/Card";
import Button from "../ui/Button";

const DASH = "—";

function formatDate(value) {
  if (!value) return DASH;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(d);
}

function formatDateTime(value) {
  if (!value) return DASH;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const t = new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit", hour12: true }).format(d);
  return `${formatDate(value)} ${t}`;
}

function Row({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted">
      <Icon size={13} className="shrink-0" aria-hidden="true" />
      <span className="text-muted">{label}</span>
      <span className="ml-auto truncate font-medium text-text" title={value}>{value}</span>
    </div>
  );
}

// Single input asset card. Same visual language as the video cards.
export default function InputCard({ input: item, onPreview, onDownload, downloading = false }) {
  const {
    filename, category, wp_type: wpType, plant, state,
    input_date: inputDate, input_time: inputTime, uploaded_time: uploadedTime,
    size, s3_path: s3Path,
  } = item;

  return (
    <Card hover className="flex flex-col p-5">
      <p className="flex items-start gap-1.5 break-all font-mono text-sm font-medium text-text" title={filename}>
        <FileText size={14} className="mt-0.5 shrink-0 text-muted" aria-hidden="true" />
        {filename}
      </p>

      <p className="mt-2 flex items-center gap-1.5 text-base font-bold text-text">
        <Building2 size={16} className="shrink-0 text-primary" aria-hidden="true" />
        {plant || DASH}
      </p>

      <div className="mt-3 space-y-1.5 border-t border-border pt-3">
        <Row icon={Layers} label="Category" value={category || DASH} />
        {wpType ? <Row icon={Film} label="WP Type" value={wpType} /> : null}
        <Row icon={MapPin} label="State" value={state || DASH} />
        <Row icon={CalendarDays} label="Input Date" value={formatDate(inputDate)} />
        <Row icon={Clock} label="Input Time" value={inputTime || DASH} />
        <Row icon={Clock3} label="Uploaded" value={formatDateTime(uploadedTime)} />
        <Row icon={HardDrive} label="Size" value={size} />
      </div>

      <div className="mt-3">
        <p className="mb-1 flex items-center gap-1 text-xs font-medium text-muted">
          <Folder size={12} aria-hidden="true" />
          S3 path
        </p>
        <p className="break-all rounded-lg border border-border bg-canvas px-2.5 py-1.5 font-mono text-[11px] leading-relaxed text-muted" title={s3Path}>
          {s3Path}
        </p>
      </div>

      <div className="mt-5 flex gap-2">
        <Button variant="secondary" size="sm" className="flex-1" onClick={() => onPreview(item)}>
          <Play size={14} aria-hidden="true" />
          Preview
        </Button>
        <Button variant="primary" size="sm" className="flex-1" onClick={() => onDownload(item)} disabled={downloading}>
          {downloading ? <Loader2 size={14} className="animate-spin" aria-hidden="true" /> : <Download size={14} aria-hidden="true" />}
          {downloading ? "Preparing…" : "Download"}
        </Button>
      </div>
    </Card>
  );
}
