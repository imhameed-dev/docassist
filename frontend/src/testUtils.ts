import type { DocumentSummary } from "./api";

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function makeDocument(overrides: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: "a".repeat(32),
    filename: "report.pdf",
    size_bytes: 2048,
    page_count: 3,
    empty_page_count: 0,
    status: "ready",
    error_code: null,
    error_message: null,
    created_at: "2026-10-17T10:00:00Z",
    ...overrides,
  };
}

type Handler = (init?: RequestInit) => Response | Promise<Response>;

/** Mock fetch by "METHOD /path". Any request without a handler fails the test loudly. */
export function mockApi(handlers: Record<string, Handler>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const key = `${init?.method ?? "GET"} ${String(input)}`;
    const handler = handlers[key];
    if (handler === undefined) throw new Error(`Unexpected request: ${key}`);
    return handler(init);
  });
}
