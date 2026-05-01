import { fetchJson } from "@/services/http/fetchJson";
import type { AssistantRawItem, AssistantTurn } from "@/screens/AssistantScreen/AssistantScreen.types";

export type AssistantApiQuery = {
  signal?: AbortSignal;
};

export type AssistantThreadsApiResponse = {
  items: Array<{
    thread_id: string;
    conversation_id: string;
    current_thread_id: string;
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
  conversation_id: string;
  current_thread_id: string;
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

export type AssistantThreadItemsApiResponse = {
  thread: AssistantThreadDetailApiResponse;
  active_turn: AssistantTurn | null;
  last_turn: AssistantTurn | null;
  items: AssistantRawItem[];
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

function apiPath(path: string, params: URLSearchParams): string {
  const search = params.toString();
  return `${path}${search ? `?${search}` : ""}`;
}

export async function getAssistantThreads(
  query: AssistantApiQuery = {},
): Promise<AssistantThreadsApiResponse> {
  const params = new URLSearchParams();
  return fetchJson<AssistantThreadsApiResponse>(apiPath("/api/threads", params), {
    signal: query.signal,
  });
}

export async function getAssistantThreadItems(
  threadId: string,
  query: AssistantApiQuery = {},
): Promise<AssistantThreadItemsApiResponse> {
  const params = new URLSearchParams({
    page: "1",
    page_size: "100",
  });
  return fetchJson<AssistantThreadItemsApiResponse>(
    apiPath(`/api/threads/${encodeURIComponent(threadId)}/items`, params),
    { signal: query.signal },
  );
}

export async function createAssistantThread(
  message: string,
): Promise<AssistantThreadCreateApiResponse> {
  const params = new URLSearchParams();
  return fetchJson<AssistantThreadCreateApiResponse>(apiPath("/api/threads", params), {
    method: "POST",
    body: JSON.stringify({
      items: [{ type: "message", data: message }],
    }),
  });
}

export async function postAssistantThreadMessage(
  threadId: string,
  message: string,
): Promise<AssistantThreadPostItemsApiResponse> {
  const params = new URLSearchParams();
  return fetchJson<AssistantThreadPostItemsApiResponse>(
    apiPath(`/api/threads/${encodeURIComponent(threadId)}/items`, params),
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
  const params = new URLSearchParams();
  return fetchJson<AssistantThreadTitleSuggestionApiResponse>(
    apiPath("/api/threads/title-suggestion", params),
    {
      method: "POST",
      body: JSON.stringify({ message }),
    },
  );
}
