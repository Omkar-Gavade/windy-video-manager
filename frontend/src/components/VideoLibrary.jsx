import { useMemo } from "react";
import { AlertCircle, FolderOpen, X } from "lucide-react";
import VideoGroup from "./VideoGroup";
import PreviewModal from "./PreviewModal";
import SkeletonCard from "./ui/SkeletonCard";
import Button from "./ui/Button";
import Card from "./ui/Card";
import { useVideoActions } from "../hooks/useVideoActions";

const SKELETON_COUNT = 3;
const LEGACY_KEY = "__legacy__";

// Group videos by plant + recording date. Legacy (metadata-less) objects go
// into a single "Legacy Uploads" group. Pure — never mutates the input.
function groupVideos(videos) {
  const groups = new Map();

  for (const video of videos) {
    const isLegacy = !video.plant || !video.recording_date;
    const key = isLegacy ? LEGACY_KEY : `${video.plant}||${video.recording_date}`;

    if (!groups.has(key)) {
      groups.set(key, {
        key,
        isLegacy,
        plant: isLegacy ? "Legacy Uploads" : video.plant,
        state: isLegacy ? null : video.state,
        recordingDate: isLegacy ? null : video.recording_date,
        videos: [],
      });
    }
    groups.get(key).videos.push(video);
  }

  const result = [...groups.values()];

  // Videos within a group: newest upload date first.
  for (const group of result) {
    group.videos = [...group.videos].sort((a, b) =>
      b.upload_date.localeCompare(a.upload_date)
    );
  }

  // Groups: legacy last; otherwise newest recording date first, then plant A→Z.
  result.sort((a, b) => {
    if (a.isLegacy) return 1;
    if (b.isLegacy) return -1;
    if (a.recordingDate !== b.recordingDate) {
      return b.recordingDate.localeCompare(a.recordingDate);
    }
    return a.plant.localeCompare(b.plant);
  });

  return result;
}

// Library section. Data is supplied by the parent; preview / download side
// effects are owned by useVideoActions. Groups recordings for presentation.
export default function VideoLibrary({ videos, loading, error, onRetry }) {
  const {
    activeVideo,
    previewUrl,
    previewLoading,
    previewError,
    openPreview,
    closePreview,
    downloadingKey,
    downloadError,
    clearDownloadError,
    download,
  } = useVideoActions();

  const groups = useMemo(() => groupVideos(videos), [videos]);

  return (
    <section aria-labelledby="library-heading">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h2 id="library-heading" className="text-lg font-semibold text-text">
            Recording Dashboard
          </h2>
          <p className="mt-0.5 text-sm text-muted">
            Recordings grouped by plant and day.
          </p>
        </div>
        {!loading && !error ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted">
            {videos.length} {videos.length === 1 ? "video" : "videos"}
          </span>
        ) : null}
      </div>

      {downloadError ? (
        <div className="mb-4 flex items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
          <span className="inline-flex items-center gap-2">
            <AlertCircle size={16} className="text-red-500" aria-hidden="true" />
            {downloadError}
          </span>
          <button
            type="button"
            onClick={clearDownloadError}
            aria-label="Dismiss"
            className="text-red-400 hover:text-red-600"
          >
            <X size={16} />
          </button>
        </div>
      ) : null}

      <LibraryContent
        loading={loading}
        error={error}
        groups={groups}
        onRetry={onRetry}
        onPreview={openPreview}
        onDownload={download}
        downloadingKey={downloadingKey}
      />

      <PreviewModal
        isOpen={Boolean(activeVideo)}
        onClose={closePreview}
        video={activeVideo}
        url={previewUrl}
        loading={previewLoading}
        error={previewError}
        onDownload={download}
        downloading={downloadingKey === activeVideo?.key}
      />
    </section>
  );
}

function LibraryContent({
  loading,
  error,
  groups,
  onRetry,
  onPreview,
  onDownload,
  downloadingKey,
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: SKELETON_COUNT }).map((_, index) => (
          <SkeletonCard key={index} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="flex flex-col items-center px-6 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-red-500">
          <AlertCircle size={22} aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-sm font-semibold text-text">
          Couldn&apos;t load videos
        </h3>
        <p className="mt-1 max-w-sm text-sm text-muted">{error}</p>
        <Button variant="secondary" size="md" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      </Card>
    );
  }

  if (groups.length === 0) {
    return (
      <Card className="flex flex-col items-center px-6 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <FolderOpen size={22} aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-sm font-semibold text-text">No videos yet</h3>
        <p className="mt-1 max-w-sm text-sm text-muted">
          Uploaded videos will appear here.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <VideoGroup
          key={group.key}
          group={group}
          onPreview={onPreview}
          onDownload={onDownload}
          downloadingKey={downloadingKey}
        />
      ))}
    </div>
  );
}
