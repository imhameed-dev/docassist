import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AskQuestion from "./AskQuestion";
import { jsonResponse, makeDocument, mockApi } from "./testUtils";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AskQuestion", () => {
  const document = makeDocument({
    id: "a".repeat(32),
    filename: "report.pdf",
  });

  it("shows an answer with its source filename, page, and excerpt", async () => {
    mockApi({
      "POST /api/answer": () =>
        jsonResponse({
          answer: "Secure retrieval preserves page citations.",
          insufficient_evidence: false,
          citations: [
            {
              document_id: document.id,
              filename: "report.pdf",
              page_number: 2,
              excerpt: "Page citations are preserved.",
            },
          ],
        }),
    });

    render(<AskQuestion documents={[document]} />);

    await userEvent.type(
      screen.getByLabelText("Your question"),
      "How are citations preserved?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Ask question" }));

    expect(
      await screen.findByText("Secure retrieval preserves page citations."),
    ).toBeInTheDocument();
    expect(screen.getByText("report.pdf", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("Page citations are preserved.")).toBeInTheDocument();
    expect(screen.getByText(/Page 2/)).toBeInTheDocument();
  });

  it("shows the insufficient-evidence answer without claiming sources", async () => {
    mockApi({
      "POST /api/answer": () =>
        jsonResponse({
          answer: "The documents do not contain enough evidence to answer this question.",
          insufficient_evidence: true,
          citations: [],
        }),
    });

    render(<AskQuestion documents={[document]} />);

    await userEvent.type(
      screen.getByLabelText("Your question"),
      "What is not covered?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Ask question" }));

    expect(
      await screen.findByText(
        "The documents do not contain enough evidence to answer this question.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sources" })).not.toBeInTheDocument();
  });

  it("shows an error when the answer request fails", async () => {
    mockApi({
      "POST /api/answer": () =>
        jsonResponse(
          { detail: { code: "internal_error", message: "Answer service unavailable." } },
          500,
        ),
    });

    render(<AskQuestion documents={[document]} />);

    await userEvent.type(
      screen.getByLabelText("Your question"),
      "Summarize the report.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Ask question" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("requires a readable document before showing the question form", () => {
    render(
      <AskQuestion
        documents={[
          makeDocument({
            status: "needs_ocr",
            error_code: "needs_ocr",
          }),
        ]}
      />,
    );

    expect(
      screen.getByText("Upload a readable PDF before asking a question."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Your question")).not.toBeInTheDocument();
  });
});
