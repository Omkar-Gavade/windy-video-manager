// Surface primitive: white rounded panel with a soft border and shadow.
// `hover` opts the card into a subtle lift interaction.
export default function Card({ hover = false, className = "", children, ...props }) {
  const classes = [
    "rounded-2xl border border-border bg-card shadow-soft",
    hover ? "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lift" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
}
