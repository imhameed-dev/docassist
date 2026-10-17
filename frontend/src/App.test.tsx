import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";

const okBody = { status: "ok", app: "Test App", environment: "test", version: "9.9.9" };

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("shows a loading state, then the backend status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(okBody));
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking backend");
    expect(await screen.findByText(/Backend is running: Test App v9\.9\.9/)).toBeInTheDocument();
  });

  it("shows an accessible error when the backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the backend");
  });

  it("shows an error for a non-OK HTTP response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({}, 500));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 500");
  });

  it("shows an error for a malformed response body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ unexpected: true }));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("unexpected response");
  });

  it("retries when the Retry button is pressed", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(jsonResponse(okBody));
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText(/Backend is running/)).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });
});
