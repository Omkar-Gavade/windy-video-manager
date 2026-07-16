// Loading placeholder that mirrors the VideoCard layout.
// Shown while the library is fetching in a later milestone.
export default function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-soft">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 animate-pulse rounded-xl bg-border/70" />
        <div className="flex-1 space-y-2">
          <div className="h-3.5 w-2/3 animate-pulse rounded bg-border/70" />
          <div className="h-3 w-1/3 animate-pulse rounded bg-border/60" />
        </div>
      </div>

      <div className="mt-5 space-y-2">
        <div className="h-3 w-1/2 animate-pulse rounded bg-border/60" />
        <div className="h-8 w-full animate-pulse rounded-lg bg-border/50" />
      </div>

      <div className="mt-5 flex gap-2">
        <div className="h-9 flex-1 animate-pulse rounded-lg bg-border/60" />
        <div className="h-9 flex-1 animate-pulse rounded-lg bg-border/60" />
      </div>
    </div>
  );
}
