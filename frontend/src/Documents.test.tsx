import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Documents from "./Documents";
import { jsonResponse, makeDocument, mockApi } from "./testUtils";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Documents", () => {
  it("shows an empty state when there are no documents", async () => {
    mockApi({ "GET /api/documents": () => jsonResponse([]) });
    render(<Documents />);
    expect(screen.getByText("Loading documents…")).toBeInTheDocument();
    expect(await screen.findByText(/No documents yet/)).toBeInTheDocument();
  });

  it("lists documents with their status and any explanation", async () => {
    mockApi({
      "GET /api/documents": () =>
        jsonResponse([
          makeDocument({ id: "1".repeat(32), filename: "good.pdf", empty_page_count: 1 }),
          makeDocument({
            id: "2".repeat(32),
            filename: "scan.pdf",
            status: "needs_ocr",
            error_code: "needs_ocr",
            error_message: "No selectable text was found.",
          }),
          makeDocument({
            id: "3".repeat(32),
            filename: "broken.pdf",
            status: "failed",
            page_count: 0,
            error_code: "corrupted",
            error_message: "This PDF is corrupted or could not be read.",
          }),
        ]),
    });
    render(<Documents />);
    expect(await screen.findByText("good.pdf")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText(/1 page without text/)).toBeInTheDocument();
    expect(screen.getByText("OCR required")).toBeInTheDocument();
    expect(screen.getByText("No selectable text was found.")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("This PDF is corrupted or could not be read.")).toBeInTheDocument();
  });

  it("shows an error with a working Retry when the list cannot be loaded", async () => {
    let calls = 0;
    mockApi({
      "GET /api/documents": () => {
        calls += 1;
        return calls === 1 ? jsonResponse({}, 500) : jsonResponse([makeDocument()]);
      },
    });
    render(<Documents />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load documents");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("report.pdf")).toBeInTheDocument();
  });

  it("uploads the chosen file as multipart form data and shows the result", async () => {
    const captured: { body?: BodyInit | null } = {};
    mockApi({
      "GET /api/documents": () => jsonResponse([]),
      "POST /api/documents": (init) => {
        captured.body = init?.body;
        return jsonResponse(makeDocument({ filename: "new.pdf" }), 201);
      },
    });
    render(<Documents />);
    await screen.findByText(/No documents yet/);

    const file = new File(["%PDF-1.4"], "new.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Upload PDF"), file);

    expect(await screen.findByText("new.pdf")).toBeInTheDocument();
    expect(captured.body).toBeInstanceOf(FormData);
    const sent = (captured.body as FormData).get("file") as File;
    expect(sent.name).toBe("new.pdf");
  });

  it("shows the server's message when an upload is rejected", async () => {
    mockApi({
      "GET /api/documents": () => jsonResponse([]),
      "POST /api/documents": () =>
        jsonResponse({ detail: { code: "not_a_pdf", message: "The file is not a valid PDF." } }, 415),
    });
    render(<Documents />);
    await screen.findByText(/No documents yet/);

    const file = new File(["hello"], "fake.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Upload PDF"), file);

    expect(await screen.findByRole("alert")).toHaveTextContent("The file is not a valid PDF.");
    expect(screen.getByText(/No documents yet/)).toBeInTheDocument();
  });

  it("deletes a document after confirmation", async () => {
    const doc = makeDocument();
    mockApi({
      "GET /api/documents": () => jsonResponse([doc]),
      [`DELETE /api/documents/${doc.id}`]: () => new Response(null, { status: 204 }),
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<Documents />);

    await userEvent.click(await screen.findByRole("button", { name: "Delete report.pdf" }));

    await waitFor(() => expect(screen.queryByText("report.pdf")).not.toBeInTheDocument());
    expect(screen.getByText(/No documents yet/)).toBeInTheDocument();
  });

  it("does nothing when deletion is not confirmed", async () => {
    const fetchSpy = mockApi({ "GET /api/documents": () => jsonResponse([makeDocument()]) });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<Documents />);

    await userEvent.click(await screen.findByRole("button", { name: "Delete report.pdf" }));

    expect(screen.getByText("report.pdf")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(1); // only the initial list request
  });

  it("keeps the document and shows an error if deletion fails", async () => {
    const doc = makeDocument();
    mockApi({
      "GET /api/documents": () => jsonResponse([doc]),
      [`DELETE /api/documents/${doc.id}`]: () => jsonResponse({}, 500),
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<Documents />);

    await userEvent.click(await screen.findByRole("button", { name: "Delete report.pdf" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 500");
    expect(screen.getByText("report.pdf")).toBeInTheDocument();
  });
});
