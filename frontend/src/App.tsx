import { useEffect, useState } from "react";

import { fetchHealth, type HealthStatus } from "./api";

type State =
  | { kind: "loading" }
  | { kind: "ok"; health: HealthStatus }
  | { kind: "error"; message: string };

export default function App() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    fetchHealth(controller.signal)
      .then((health) => setState({ kind: "ok", health }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          kind: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      });
    return () => controller.abort();
  }, [attempt]);

  return (
    <main>
      <h1>Private AI Document Assistant</h1>
      <section aria-labelledby="backend-heading">
        <h2 id="backend-heading">Backend status</h2>
        {state.kind === "loading" && <p role="status">Checking backend…</p>}
        {state.kind === "ok" && (
          <p role="status">
            Backend is running: {state.health.app} v{state.health.version} (
            {state.health.environment})
          </p>
        )}
        {state.kind === "error" && (
          <div role="alert">
            <p>Could not reach the backend. {state.message}</p>
            <button type="button" onClick={() => setAttempt((n) => n + 1)}>
              Retry
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
