type UnauthorizedHandler = () => void;
type ApiRequestInit = RequestInit & {
  suppressUnauthorizedHandler?: boolean;
};

let unauthorizedHandler: UnauthorizedHandler | null = null;

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  } catch {
    // Fall through to the status fallback for non-JSON or empty error responses.
  }
  return response.statusText || `Request failed with ${response.status}`;
}

export async function fetchJson<T>(
  input: RequestInfo | URL,
  init: ApiRequestInit = {},
): Promise<T> {
  const response = await fetch(input, {
    credentials: "include",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    if (response.status === 401 && !init.suppressUnauthorizedHandler) {
      unauthorizedHandler?.();
    }
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}
