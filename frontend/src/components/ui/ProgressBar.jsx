// Determinate progress bar. `value` is a 0-100 percentage.
// Rendering only — the driving value is wired in the upload milestone.
export default function ProgressBar({ value = 0, className = "" }) {
  const pct = Math.min(100, Math.max(0, value));

  return (
    <div
      className={["h-2 w-full overflow-hidden rounded-full bg-border/70", className]
        .filter(Boolean)
        .join(" ")}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
