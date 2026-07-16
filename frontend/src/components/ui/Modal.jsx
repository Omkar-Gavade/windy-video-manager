import { useEffect } from "react";
import { X } from "lucide-react";
import Button from "./Button";

// Accessible centered modal primitive.
// Handles overlay click + Escape to close and locks body scroll while open.
// Content (and any actions) are provided by the caller via children/footer.
export default function Modal({ isOpen, onClose, title, children, footer }) {
  useEffect(() => {
    if (!isOpen) return undefined;

    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose?.();
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="absolute inset-0 bg-text/40 backdrop-blur-sm animate-[fadeIn_150ms_ease-out]"
        onClick={onClose}
      />

      <div className="relative z-10 w-full max-w-2xl animate-[scaleIn_180ms_ease-out]">
        <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-lift">
          <header className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold text-text">{title}</h2>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 px-0"
              aria-label="Close"
              onClick={onClose}
            >
              <X size={18} />
            </Button>
          </header>

          <div className="p-5">{children}</div>

          {footer ? (
            <footer className="flex justify-end gap-2 border-t border-border px-5 py-4">
              {footer}
            </footer>
          ) : null}
        </div>
      </div>
    </div>
  );
}
