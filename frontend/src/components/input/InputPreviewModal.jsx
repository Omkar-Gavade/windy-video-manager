import { useEffect, useState } from "react";
import { Download, AlertCircle, Loader2, FileX2 } from "lucide-react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { getContent } from "../../services/inputApi";

function extOf(name = "") {
  const lower = name.toLowerCase();
  const dot = lower.lastIndexOf(".");
  return dot === -1 ? "" : lower.slice(dot);
}

const IMAGE = new Set([".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]);
const VIDEO = new Set([".mp4", ".webm", ".mov"]);

function kindOf(ext) {
  if (IMAGE.has(ext)) return "image";
  if (VIDEO.has(ext)) return "video";
  if (ext === ".pdf") return "pdf";
  if (ext === ".json") return "json";
  if (ext === ".csv") return "csv";
  if (ext === ".txt") return "text";
  return "other";
}

const TEXT_KINDS = new Set(["json", "csv", "text"]);

// Very small CSV parser (handles simple quoted fields) -> array of rows.
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (c === '"') inQuotes = false;
      else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.length && !(r.length === 1 && r[0] === ""));
}

// Minimal JSON syntax highlighter -> HTML string.
function highlightJson(text) {
  const pretty = JSON.stringify(JSON.parse(text), null, 2);
  const escaped = pretty
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "text-primary"; // number
      if (/^"/.test(match)) cls = /:$/.test(match) ? "font-semibold text-text" : "text-success";
      else if (/true|false/.test(match)) cls = "text-primary";
      else if (/null/.test(match)) cls = "text-muted";
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

// Input preview modal. Renders each supported type inline (never forces a
// download when preview is possible).
export default function InputPreviewModal({
  isOpen, onClose, input: item, url, loading, error, onDownload, downloading = false,
}) {
  const ext = extOf(item?.filename);
  const kind = kindOf(ext);

  const [content, setContent] = useState(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState(null);

  useEffect(() => {
    if (!isOpen || !item?.key || !TEXT_KINDS.has(kind)) {
      setContent(null);
      setContentError(null);
      return undefined;
    }
    const controller = new AbortController();
    setContentLoading(true);
    setContentError(null);
    setContent(null);
    getContent(item.key, controller.signal)
      .then((data) => setContent(data.content ?? ""))
      .catch((err) => {
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setContentError(err.message);
      })
      .finally(() => setContentLoading(false));
    return () => controller.abort();
  }, [isOpen, item?.key, kind]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={item?.filename || "Preview"}
      footer={
        <>
          <Button variant="secondary" size="md" onClick={onClose}>Close</Button>
          <Button variant="primary" size="md" onClick={() => onDownload(item)} disabled={downloading}>
            {downloading ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <Download size={16} aria-hidden="true" />}
            Download
          </Button>
        </>
      }
    >
      <div className="h-[65vh] w-full overflow-auto rounded-xl bg-canvas">
        <Body
          kind={kind}
          url={url}
          filename={item?.filename}
          urlLoading={loading}
          urlError={error}
          content={content}
          contentLoading={contentLoading}
          contentError={contentError}
        />
      </div>
    </Modal>
  );
}

function Centered({ children }) {
  return <div className="flex h-full w-full items-center justify-center px-6 text-center text-muted">{children}</div>;
}

function Body({ kind, url, filename, urlLoading, urlError, content, contentLoading, contentError }) {
  const isText = TEXT_KINDS.has(kind);
  const loading = isText ? contentLoading : urlLoading;
  const error = isText ? contentError : urlError;

  if (loading) return <Centered><Loader2 size={28} className="animate-spin" aria-hidden="true" /></Centered>;
  if (error) return <Centered><div className="flex flex-col items-center gap-2"><AlertCircle size={24} aria-hidden="true" /><p className="text-sm">{error}</p></div></Centered>;

  if (kind === "image" && url) {
    return <div className="flex h-full w-full items-center justify-center bg-text/95"><img src={url} alt={filename} className="max-h-full max-w-full object-contain" /></div>;
  }
  if (kind === "video" && url) {
    return <video src={url} controls autoPlay className="h-full w-full bg-black">Your browser does not support the video tag.</video>;
  }
  if (kind === "pdf" && url) {
    return <iframe src={url} title={filename} className="h-full w-full border-0 bg-white" />;
  }
  if (kind === "json" && content != null) {
    let html;
    try { html = highlightJson(content); }
    catch { html = null; }
    return html
      ? <pre className="m-0 whitespace-pre-wrap break-words p-4 font-mono text-xs leading-relaxed text-text" dangerouslySetInnerHTML={{ __html: html }} />
      : <pre className="m-0 whitespace-pre-wrap break-words p-4 font-mono text-xs text-text">{content}</pre>;
  }
  if (kind === "csv" && content != null) {
    const rows = parseCsv(content);
    if (rows.length === 0) return <Centered>Empty file.</Centered>;
    const [header, ...body] = rows;
    return (
      <div className="p-3">
        <table className="w-full border-collapse text-left font-mono text-xs">
          <thead>
            <tr>
              {header.map((h, i) => (
                <th key={i} className="border border-border bg-primary/10 px-2.5 py-1.5 font-semibold text-text">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((r, ri) => (
              <tr key={ri} className={ri % 2 ? "bg-card" : ""}>
                {header.map((_, ci) => (
                  <td key={ci} className="border border-border px-2.5 py-1.5 text-muted">{r[ci] ?? ""}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (kind === "text" && content != null) {
    return <pre className="m-0 whitespace-pre-wrap break-words p-4 font-mono text-xs leading-relaxed text-text">{content}</pre>;
  }

  return (
    <Centered>
      <div className="flex flex-col items-center gap-2">
        <FileX2 size={28} aria-hidden="true" />
        <p className="text-sm">Preview not available.</p>
        <p className="text-xs">Use Download to open this file.</p>
      </div>
    </Centered>
  );
}
