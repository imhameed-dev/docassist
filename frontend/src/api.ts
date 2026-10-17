export interface HealthStatus {
  status: "ok";
  app: string;
  environment: string;
  version: string;
}

function isHealthStatus(value: unknown): value is HealthStatus {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    v.status === "ok" &&
    typeof v.app === "string" &&
    typeof v.environment === "string" &&
    typeof v.version === "string"
  );
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
