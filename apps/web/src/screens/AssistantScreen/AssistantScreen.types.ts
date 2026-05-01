export type AssistantThreadStatus =
  | "ready"
  | "retrieving"
  | "streaming"
  | "queued"
  | "draft"
  | "error";

export type AssistantMessageKind =
  | "message"
  | "tool_call"
  | "tool_result"
  | "hosted_tool_event"
  | "reasoning";

export type AssistantRawItem = {
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

export type AssistantMessage = {
  id: string;
  seq?: number | null;
  kind: AssistantMessageKind;
  role: "user" | "assistant" | null;
  title: string;
  content: string;
  timestamp: string;
  detailTitle?: string;
  detailBody?: string;
  rawJson?: string;
  rawItem?: AssistantRawItem;
};

export type AssistantThread = {
  id: string;
  backendThreadId: string | null;
  title: string;
  summary: string;
  status: AssistantThreadStatus;
  updatedAt: string;
  messages: AssistantMessage[];
  isDraft?: boolean;
  itemsLoaded?: boolean;
};

export type AssistantTurn = {
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
};

