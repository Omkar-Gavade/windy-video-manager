// Reusable button primitive with a small set of visual variants.
// Behaviour (onClick handlers) is supplied by callers in later milestones.

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium " +
  "transition-all duration-150 focus:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-card " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const variants = {
  primary: "bg-primary text-white shadow-soft hover:bg-primary/90 active:bg-primary",
  secondary:
    "bg-white text-text border border-border hover:bg-canvas hover:border-muted/40",
  ghost: "bg-transparent text-muted hover:bg-canvas hover:text-text",
};

const sizes = {
  sm: "h-8 px-3",
  md: "h-10 px-4",
};

export default function Button({
  variant = "primary",
  size = "md",
  type = "button",
  className = "",
  children,
  ...props
}) {
  const classes = [base, variants[variant], sizes[size], className]
    .filter(Boolean)
    .join(" ");

  return (
    <button type={type} className={classes} {...props}>
      {children}
    </button>
  );
}
