import { useState } from "react";
import BackendStatus from "./BackendStatus";
import Documents from "./Documents";
import AskQuestion from "./AskQuestion";
import type { DocumentSummary } from "./api";

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);

  return (
    <main>
      <h1>Private AI Document Assistant</h1>
      <Documents onDocumentsChange={setDocuments} />
      <AskQuestion documents={documents} />
      <BackendStatus />
    </main>
  );
}
