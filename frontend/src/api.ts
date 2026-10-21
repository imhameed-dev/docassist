export interface HealthStatus {
  status: "ok";
  app: string;
  environment: string;
  version: string;
}

export type DocumentStatus = "ready" | "needs_ocr" | "failed";

export interface DocumentSummary {
  id: string;
  filename: string;
  size_bytes: number;
  page_count: number;
  empty_page_count: number;
  status: DocumentStatus;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
}

/** An error returned by (or while calling) the backend, with a message safe to show. */
export class ApiError extends Error {
  readonly code: string | null;
  readonly status: number;

  constructor(message: string, code: string | null = null, status = 0) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isHealthStatus(value: unknown): value is HealthStatus {
  return (
    isRecord(value) &&
    value.status === "ok" &&
    typeof value.app === "string" &&
    typeof value.environment === "string" &&
    typeof value.version === "string"
  );
}

function isDocumentSummary(value: unknown): value is DocumentSummary {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.filename === "string" &&
    typeof value.size_bytes === "number" &&
    typeof value.page_count === "number" &&
    typeof value.empty_page_count === "number" &&
    (value.status === "ready" || value.status === "needs_ocr" || value.status === "failed") &&
    (value.error_message === null || typeof value.error_message === "string") &&
    typeof value.created_at === "string"
  );
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = `Request failed (HTTP ${response.status})`;
  let code: string | null = null;
  try {
    const body: unknown = await response.json();
    const detail = isRecord(body) ? body.detail : undefined;
    if (isRecord(detail) && typeof detail.message === "string") {
      message = detail.message;
      code = typeof detail.code === "string" ? detail.code : null;
    }
  } catch {
    // The body was not JSON (for example a proxy error page): keep the generic message.
  }
  return new ApiError(message, code, response.status);
}

/** Ask the backend whether it is up. Rejects with an Error on any failure. */
export async function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  const response = await fetch("/api/health", { signal });
  if (!response.ok) {
    throw new Error(`Backend responded with HTTP ${response.status}`);
  }
  const data: unknown = await response.json();
  if (!isHealthStatus(data)) {
    throw new Error("Backend returned an unexpected response");
  }
  return data;
}

export async function listDocuments(signal?: AbortSignal): Promise<DocumentSummary[]> {
  const response = await fetch("/api/documents", { signal });
  if (!response.ok) throw await errorFromResponse(response);
  const data: unknown = await response.json();
  if (!Array.isArray(data) || !data.every(isDocumentSummary)) {
    throw new Error("Backend returned an unexpected response");
  }
  return data;
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const form = new FormData();
  form.append("file", file); // the browser sets the multipart Content-Type itself
  const response = await fetch("/api/documents", { method: "POST", body: form });
  if (!response.ok) throw await errorFromResponse(response);
  const data: unknown = await response.json();
  if (!isDocumentSummary(data)) {
    throw new Error("Backend returned an unexpected response");
  }
  return data;
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`/api/documents/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!response.ok) throw await errorFromResponse(response);
}

export interface Citation {
  document_id: string;
  filename: string;
  page_number: number;
  excerpt: string;
}

export interface AnswerResult {
  answer: string;
  insufficient_evidence: boolean;
  citations: Citation[];
}

function isCitation(value: unknown): value is Citation {
  return (
    isRecord(value) &&
    typeof value.document_id === "string" &&
    typeof value.filename === "string" &&
    typeof value.page_number === "number" &&
    typeof value.excerpt === "string"
  );
}

function isAnswerResult(value: unknown): value is AnswerResult {
  return (
    isRecord(value) &&
    typeof value.answer === "string" &&
    typeof value.insufficient_evidence === "boolean" &&
    Array.isArray(value.citations) &&
    value.citations.every(isCitation)
  );
}

export async function askQuestion(
  question: string,
  documentId?: string,
): Promise<AnswerResult> {
  const response = await fetch("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      ...(documentId === undefined ? {} : { document_id: documentId }),
    }),
  });

  if (!response.ok) throw await errorFromResponse(response);

  const data: unknown = await response.json();
  if (!isAnswerResult(data)) {
    throw new Error("Backend returned an unexpected answer response");
  }
  return data;
}
