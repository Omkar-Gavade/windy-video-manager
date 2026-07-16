import { Video } from "lucide-react";
import { NavLink } from "react-router-dom";
import Container from "./ui/Container";

const navLinkClasses = ({ isActive }) =>
  [
    "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
    isActive ? "bg-primary/10 text-primary" : "text-muted hover:text-text",
  ].join(" ");

// Top navigation: brand mark + application title + Videos/Documents links.
export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card/80 backdrop-blur">
      <Container>
        <div className="flex h-16 items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white shadow-soft">
            <Video size={18} aria-hidden="true" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-text">S3 Video Manager</p>
            <p className="text-xs text-muted">Internal video storage</p>
          </div>

          <nav className="ml-auto flex items-center gap-1" aria-label="Primary">
            <NavLink to="/" end className={navLinkClasses}>
              Videos
            </NavLink>
            <NavLink to="/documents" className={navLinkClasses}>
              Documents
            </NavLink>
          </nav>
        </div>
      </Container>
    </header>
  );
}
