import type {
  AssistantMessage,
  AssistantThread,
  AssistantThreadStatus,
} from "../../features/assistant/types";

export type AssistantThreadsApiResponse = {
  items: Array<{
    thread_id: string;
    thread_kind: string;
    agent_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    preview_text: string;
    status: string;
    phase: string;
  }>;
  total: number;
  page: number;
  page_size: number;
};

export type AssistantThreadDetailApiResponse = {
  thread_id: string;
  thread_kind: string;
  agent_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: string;
  phase: string;
  active_turn_id: string | null;
  last_turn_id: string | null;
  execution_options: Record<string, object>;
  metadata: Record<string, object>;
};

export type AssistantThreadItemApiResponse = {
  summary: {
    title: string;
    detail: string;
  };
  record: {
    item_id: string;
    seq: number | null;
    item_type: string;
    role: string | null;
    name: string | null;
    content_text: string | null;
    arguments: Record<string, unknown>;
    result: Record<string, unknown>;
    provider_item_id: string | null;
    provider_item_type: string | null;
    provider_payload: Record<string, unknown>;
    metadata: Record<string, unknown>;
    created_at: string;
  };
};

export type AssistantThreadItemsApiResponse = {
  thread: AssistantThreadDetailApiResponse;
  active_turn: {
    turn_id: string;
    thread_id: string;
    agent_id: string;
    status: string;
    phase: string;
    queued_at: string;
    started_at: string;
    completed_at: string | null;
    provider: string | null;
    model: string | null;
    claim_worker_id: string | null;
    heartbeat_at: string | null;
    provider_response_id: string | null;
    provider_conversation_id: string | null;
    usage: Record<string, object>;
    error: Record<string, object>;
    metadata: Record<string, object>;
    execution_options: Record<string, object>;
  } | null;
  last_turn: {
    turn_id: string;
    thread_id: string;
    agent_id: string;
    status: string;
    phase: string;
    queued_at: string;
    started_at: string;
    completed_at: string | null;
    provider: string | null;
    model: string | null;
    claim_worker_id: string | null;
    heartbeat_at: string | null;
    provider_response_id: string | null;
    provider_conversation_id: string | null;
    usage: Record<string, object>;
    error: Record<string, object>;
    metadata: Record<string, object>;
    execution_options: Record<string, object>;
  } | null;
  items: AssistantThreadItemApiResponse[];
  total: number;
  page: number;
  page_size: number;
};

export type AssistantThreadCreateApiResponse = {
  thread: AssistantThreadDetailApiResponse;
  turn: {
    turn_id: string;
    status: string;
    phase: string;
  } | null;
};

export type AssistantThreadPostItemsApiResponse = {
  thread: AssistantThreadDetailApiResponse;
  turn: {
    turn_id: string;
    status: string;
    phase: string;
  };
};

export type AssistantThreadTitleSuggestionApiResponse = {
  title: string;
};

export type AssistantThreadUpdateTitleApiResponse =
  AssistantThreadDetailApiResponse;

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

function compactText(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function preserveMessageText(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatRelativeTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const diffMs = date.getTime() - Date.now();
  const absMs = Math.abs(diffMs);
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

  if (absMs < hour) {
    return formatter.format(Math.round(diffMs / minute), "minute");
  }
  if (absMs < day) {
    return formatter.format(Math.round(diffMs / hour), "hour");
  }
  return formatter.format(Math.round(diffMs / day), "day");
}

function stringifyDetail(value: unknown): string {
  if (value == null) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function isImageGenerationItem(item: AssistantThreadItemApiResponse): boolean {
  return (
    item.record.item_type === "hosted_tool_event" &&
    (item.record.name === "image_generation_call" ||
      item.record.provider_item_type === "image_generation_call")
  );
}

function sanitizedDebugItem(
  item: AssistantThreadItemApiResponse,
): AssistantThreadItemApiResponse {
  if (!isImageGenerationItem(item)) {
    return item;
  }

  const providerPayload = { ...item.record.provider_payload };
  if (typeof providerPayload.result === "string" && providerPayload.result.length > 0) {
    providerPayload.result = "<base 64 image bytes>";
  }

  return {
    ...item,
    summary: {
      ...item.summary,
      detail: "Image generation call",
    },
    record: {
      ...item.record,
      provider_payload: providerPayload,
    },
  };
}

function mapStatus(status: string, phase: string): AssistantThreadStatus {
  if (status === "queued" || phase === "queued") {
    return "queued";
  }
  if (status === "running" || phase === "running" || phase === "working") {
    return "streaming";
  }
  if (status === "error" || phase === "error" || status === "failed") {
    return "error";
  }
  return "ready";
}

async function fetchJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function threadSummaryFromApiItem(
  item: AssistantThreadsApiResponse["items"][number],
): AssistantThread {
  return {
    id: item.thread_id,
    backendThreadId: item.thread_id,
    title: item.title,
    summary: compactText(item.preview_text) || "No messages yet.",
    status: mapStatus(item.status, item.phase),
    updatedAt: formatRelativeTime(item.updated_at),
    messages: [],
    itemsLoaded: false,
  };
}

export function threadFromDetailApi(
  detail: AssistantThreadDetailApiResponse,
  current?: AssistantThread,
): AssistantThread {
  return {
    id: detail.thread_id,
    backendThreadId: detail.thread_id,
    title: detail.title,
    summary: current?.summary ?? "No messages yet.",
    status: mapStatus(detail.status, detail.phase),
    updatedAt: formatRelativeTime(detail.updated_at),
    messages: current?.messages ?? [],
    itemsLoaded: current?.itemsLoaded ?? false,
  };
}

export function messageFromApiItem(item: AssistantThreadItemApiResponse): AssistantMessage {
  const detailSections = [
    item.summary.detail ? item.summary.detail : "",
    Object.keys(item.record.arguments).length
      ? `Arguments\n${stringifyDetail(item.record.arguments)}`
      : "",
    Object.keys(item.record.result).length
      ? `Result\n${stringifyDetail(item.record.result)}`
      : "",
    Object.keys(item.record.provider_payload).length
      ? `Provider payload\n${stringifyDetail(sanitizedDebugItem(item).record.provider_payload)}`
      : "",
    Object.keys(item.record.metadata).length
      ? `Metadata\n${stringifyDetail(item.record.metadata)}`
      : "",
  ].filter(Boolean);

  return {
    id: item.record.item_id,
    seq: item.record.seq,
    kind: (item.record.item_type as AssistantMessage["kind"]) ?? "message",
    role:
      item.record.item_type === "message"
        ? item.record.role === "assistant"
          ? "assistant"
          : "user"
        : null,
    title: item.summary.title,
    content:
      (item.record.item_type === "message"
        ? preserveMessageText(item.record.content_text)
        : compactText(item.record.content_text)) ||
      compactText(item.summary.detail) ||
      item.summary.title,
    timestamp: formatTime(item.record.created_at),
    detailTitle: item.summary.title,
    detailBody: detailSections.join("\n\n"),
    rawJson: stringifyDetail({
      summary: sanitizedDebugItem(item).summary,
      record: sanitizedDebugItem(item).record,
    }),
    rawItem: item,
  };
}

export async function getAssistantThreads(
  signal?: AbortSignal,
): Promise<AssistantThreadsApiResponse> {
  return fetchJson<AssistantThreadsApiResponse>("/threads", { signal });
}

export async function getAssistantThreadDetail(
  threadId: string,
  signal?: AbortSignal,
): Promise<AssistantThreadDetailApiResponse> {
  return fetchJson<AssistantThreadDetailApiResponse>(
    `/threads/${encodeURIComponent(threadId)}`,
    { signal },
  );
}

export async function getAssistantThreadItems(
  threadId: string,
  signal?: AbortSignal,
): Promise<AssistantThreadItemsApiResponse> {
  return fetchJson<AssistantThreadItemsApiResponse>(
    `/threads/${encodeURIComponent(threadId)}/items?page=1&page_size=100`,
    { signal },
  );
}

export async function createAssistantThread(
  message: string,
): Promise<AssistantThreadCreateApiResponse> {
  return fetchJson<AssistantThreadCreateApiResponse>("/threads", {
    method: "POST",
    body: JSON.stringify({
      items: [{ type: "text", data: message }],
    }),
  });
}

export async function postAssistantThreadMessage(
  threadId: string,
  message: string,
): Promise<AssistantThreadPostItemsApiResponse> {
  return fetchJson<AssistantThreadPostItemsApiResponse>(
    `/threads/${encodeURIComponent(threadId)}/items`,
    {
      method: "POST",
      body: JSON.stringify({
        items: [{ type: "message", data: message }],
      }),
    },
  );
}

export async function suggestAssistantThreadTitle(
  message: string,
): Promise<AssistantThreadTitleSuggestionApiResponse> {
  return fetchJson<AssistantThreadTitleSuggestionApiResponse>(
    "/threads/title-suggestion",
    {
      method: "POST",
      body: JSON.stringify({ message }),
    },
  );
}

export async function updateAssistantThreadTitle(
  threadId: string,
  title: string,
): Promise<AssistantThreadUpdateTitleApiResponse> {
  return fetchJson<AssistantThreadUpdateTitleApiResponse>(
    `/threads/${encodeURIComponent(threadId)}/title`,
    {
      method: "PATCH",
      body: JSON.stringify({ title }),
    },
  );
}
