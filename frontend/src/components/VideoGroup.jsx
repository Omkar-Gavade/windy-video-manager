import { Building2, MapPin, CalendarDays, Video } from "lucide-react";
import Card from "./ui/Card";
import VideoCard from "./VideoCard";

// Format a date-only value as e.g. "15 Jul 2026".
function formatRecordingDate(value) {
  if (!value) return "Unknown Recording Date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

// A plant + recording-date group: header (plant/state/date/count) over a
// responsive grid of recording cards.
export default function VideoGroup({ group, onPreview, onDownload, downloadingKey }) {
  const { plant, state, recordingDate, isLegacy, videos } = group;
  const count = videos.length;

  return (
    <Card className="p-6">
      <header className="mb-5 border-b border-border pb-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h3 className="flex items-center gap-2 text-xl font-bold text-text">
              <Building2 size={20} className="shrink-0 text-primary" aria-hidden="true" />
              {plant}
            </h3>
            {!isLegacy ? (
              <p className="mt-1.5 flex items-center gap-1.5 text-sm text-muted">
                <MapPin size={14} aria-hidden="true" />
                {state}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-canvas px-3 py-1 text-xs font-medium text-muted">
              <CalendarDays size={13} aria-hidden="true" />
              {isLegacy ? formatRecordingDate(null) : `Recorded ${formatRecordingDate(recordingDate)}`}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              <Video size={13} aria-hidden="true" />
              {count} {count === 1 ? "Recording" : "Recordings"}
            </span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {videos.map((video) => (
          <VideoCard
            key={video.key}
            video={video}
            onPreview={onPreview}
            onDownload={onDownload}
            downloading={downloadingKey === video.key}
          />
        ))}
      </div>
    </Card>
  );
}
