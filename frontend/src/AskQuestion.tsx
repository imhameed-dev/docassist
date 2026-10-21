import { useState, type FormEvent } from "react";

import { askQuestion, type AnswerResult, type DocumentSummary } from "./api";

interface Props {
  documents: DocumentSummary[];
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}

export default function AskQuestion({ documents }: Props) {
  const [question, setQuestion] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [answer, setAnswer] = useState<AnswerResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readyDocuments = documents.filter((doc) => doc.status === "ready");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const result = await askQuestion(trimmed, documentId || undefined);
      setAnswer(result);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="ask-heading">
      <h2 id="ask-heading">Ask your documents</h2>
      <p>Ask a question and review the source passages and page numbers.</p>

      {readyDocuments.length === 0 ? (
        <p>Upload a readable PDF before asking a question.</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <label htmlFor="document-select">Search in</label>
          <select
            id="document-select"
            value={documentId}
            onChange={(event) => setDocumentId(event.target.value)}
          >
            <option value="">All ready documents</option>
            {readyDocuments.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}
              </option>
            ))}
          </select>

          <label htmlFor="document-question">Your question</label>
          <textarea
            id="document-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={500}
            rows={4}
            required
            placeholder="What does the document say about…?"
          />
          <p className="meta">{question.length}/500 characters</p>

          <button type="submit" disabled={loading || question.trim().length === 0}>
            {loading ? "Searching documents…" : "Ask question"}
          </button>
        </form>
      )}

      {loading && <p role="status">Searching your documents for evidence…</p>}
      {error !== null && <p role="alert">Could not answer the question. {error}</p>}

      {answer !== null && (
        <div className="answer" aria-labelledby="answer-heading" aria-live="polite">
          <h3 id="answer-heading">Answer</h3>
          {answer.insufficient_evidence ? (
            <p>{answer.answer}</p>
          ) : (
            <>
              <p className="answer-text">{answer.answer}</p>
              <h4>Sources</h4>
              {answer.citations.length === 0 ? (
                <p>No source citations were returned.</p>
              ) : (
                <ol className="citations">
                  {answer.citations.map((citation, index) => (
                    <li key={`${citation.document_id}-${citation.page_number}-${index}`}>
                      <strong>{citation.filename}</strong>
                      {" — Page "}
                      {citation.page_number}
                      <blockquote>{citation.excerpt}</blockquote>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
