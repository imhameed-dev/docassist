import { render, screen } from "@testing-library/react";

import App from "./App";
import { jsonResponse, mockApi } from "./testUtils";

afterEach(() => {
  vi.restoreAllMocks();
});

it("shows the document manager and the backend status together", async () => {
  mockApi({
    "GET /api/health": () =>
      jsonResponse({ status: "ok", app: "Test App", environment: "test", version: "1.2.3" }),
    "GET /api/documents": () => jsonResponse([]),
  });
  render(<App />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "Private AI Document Assistant",
  );
  expect(await screen.findByText(/No documents yet/)).toBeInTheDocument();
  expect(await screen.findByText(/Backend is running: Test App v1\.2\.3/)).toBeInTheDocument();
});
