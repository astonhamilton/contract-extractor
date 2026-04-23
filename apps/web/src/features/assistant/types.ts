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
  rawItem?: {
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
