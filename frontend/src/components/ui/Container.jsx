// Centered, width-constrained page wrapper with responsive gutters.
export default function Container({ className = "", children }) {
  const classes = ["mx-auto w-full max-w-5xl px-5 sm:px-6 lg:px-8", className]
    .filter(Boolean)
    .join(" ");

  return <div className={classes}>{children}</div>;
}
