import { type ChangeEvent, useEffect, useState } from "react";

import {
  type DocumentStatus,
  type DocumentSummary,
  deleteDocument,
  listDocuments,
  uploadDocument,
} from "./api";

type ListState =
  | { kind: "loading" }
  | { kind: "ready"; documents: DocumentSummary[] }
  | { kind: "error"; message: string };

const STATUS_LABEL: Record<DocumentStatus, string> = {
  ready: "Ready",
  needs_ocr: "OCR required",
  failed: "Failed",
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function describe(doc: DocumentSummary): string {
  if (doc.status === "failed") return formatSize(doc.size_bytes);
  const parts = [formatSize(doc.size_bytes), plural(doc.page_count, "page")];
  if (doc.status === "ready" && doc.empty_page_count > 0) {
    parts.push(`${plural(doc.empty_page_count, "page")} without text`);
  }
  return parts.join(" · ");
}

interface Props {
  onDocumentsChange?: (documents: DocumentSummary[]) => void;
}

export default function Documents({ onDocumentsChange }: Props) {
  const [list, setList] = useState<ListState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setList({ kind: "loading" });
    listDocuments(controller.signal)
      .then((documents) => setList({ kind: "ready", documents }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setList({ kind: "error", message: messageOf(error) });
      });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    if (list.kind === "ready") {
      onDocumentsChange?.(list.documents);
    }
  }, [list, onDocumentsChange]);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget; // capture: currentTarget is cleared after an await
    const file = input.files?.[0];
    if (file === undefined) return;
    setUploading(true);
    setActionError(null);
    try {
      const created = await uploadDocument(file);
      setList((prev) =>
        prev.kind === "ready" ? { kind: "ready", documents: [created, ...prev.documents] } : prev,
      );
    } catch (error) {
      setActionError(messageOf(error));
    } finally {
      setUploading(false);
      input.value = ""; // allow choosing the same file again
    }
  }

  async function handleDelete(doc: DocumentSummary) {
    const confirmed = window.confirm(
      `Delete "${doc.filename}"? This permanently removes the document and its extracted text.`,
    );
    if (!confirmed) return;
    setDeletingId(doc.id);
    setActionError(null);
    try {
      await deleteDocument(doc.id);
      setList((prev) =>
        prev.kind === "ready"
          ? { kind: "ready", documents: prev.documents.filter((d) => d.id !== doc.id) }
          : prev,
      );
    } catch (error) {
      setActionError(messageOf(error));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section aria-labelledby="documents-heading">
      <h2 id="documents-heading">Documents</h2>

      <div className="upload">
        <label htmlFor="pdf-upload">Upload PDF</label>
        <input
          id="pdf-upload"
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          disabled={uploading || list.kind !== "ready"}
        />
        {uploading && <p role="status">Uploading and processing…</p>}
      </div>

      {actionError !== null && <p role="alert">{actionError}</p>}

      {list.kind === "loading" && <p role="status">Loading documents…</p>}
      {list.kind === "error" && (
        <div role="alert">
          <p>Could not load documents. {list.message}</p>
          <button type="button" onClick={() => setAttempt((n) => n + 1)}>
            Retry
          </button>
        </div>
      )}
      {list.kind === "ready" && list.documents.length === 0 && (
        <p>No documents yet. Upload a PDF to get started.</p>
      )}
      {list.kind === "ready" && list.documents.length > 0 && (
        <ul className="documents">
          {list.documents.map((doc) => (
            <li key={doc.id}>
              <div className="doc-header">
                <strong>{doc.filename}</strong>
                <span className={`badge badge-${doc.status}`}>{STATUS_LABEL[doc.status]}</span>
              </div>
              <div className="meta">{describe(doc)}</div>
              {doc.error_message !== null && <p className="note">{doc.error_message}</p>}
              <button
                type="button"
                aria-label={`Delete ${doc.filename}`}
                disabled={deletingId === doc.id}
                onClick={() => void handleDelete(doc)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
