import type {
  AssistantThreadCreateApiResponse,
  AssistantThreadDetailApiResponse,
  AssistantThreadPostItemsApiResponse,
  AssistantThreadsApiResponse,
} from "@/services/assistant/assistantApi";
import type {
  AssistantMessage,
  AssistantRawItem,
  AssistantThread,
  AssistantThreadStatus,
} from "@/screens/AssistantScreen/AssistantScreen.types";

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

function isImageGenerationItem(item: AssistantRawItem): boolean {
  return (
    item.record.item_type === "hosted_tool_event" &&
    (item.record.name === "image_generation_call" ||
      item.record.provider_item_type === "image_generation_call")
  );
}

function sanitizedDebugItem(item: AssistantRawItem): AssistantRawItem {
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

export function assistantThreadSummaryFromApiItem(
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

export function assistantThreadFromDetailApi(
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

export function assistantThreadFromCreateApi(
  response: AssistantThreadCreateApiResponse,
  current?: AssistantThread,
): AssistantThread {
  return assistantThreadFromDetailApi(response.thread, current);
}

export function assistantThreadFromPostApi(
  response: AssistantThreadPostItemsApiResponse,
  current?: AssistantThread,
): AssistantThread {
  return assistantThreadFromDetailApi(response.thread, current);
}

export function assistantMessageFromApiItem(item: AssistantRawItem): AssistantMessage {
  const sanitizedItem = sanitizedDebugItem(item);
  const detailSections = [
    item.summary.detail ? item.summary.detail : "",
    Object.keys(item.record.arguments).length
      ? `Arguments\n${stringifyDetail(item.record.arguments)}`
      : "",
    Object.keys(item.record.result).length
      ? `Result\n${stringifyDetail(item.record.result)}`
      : "",
    Object.keys(item.record.provider_payload).length
      ? `Provider payload\n${stringifyDetail(sanitizedItem.record.provider_payload)}`
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
      summary: sanitizedItem.summary,
      record: sanitizedItem.record,
    }),
    rawItem: item,
  };
}

export function optimisticUserMessage(content: string): AssistantMessage {
  return {
    id: `local-${Date.now()}`,
    kind: "message",
    role: "user",
    title: "User",
    content,
    timestamp: "just now",
  };
}

export function sortedAssistantMessages(messages: AssistantMessage[]): AssistantMessage[] {
  return [...messages].sort((left, right) => {
    const leftSeq = left.seq ?? Number.MAX_SAFE_INTEGER;
    const rightSeq = right.seq ?? Number.MAX_SAFE_INTEGER;
    if (leftSeq !== rightSeq) {
      return leftSeq - rightSeq;
    }
    return left.timestamp.localeCompare(right.timestamp);
  });
}

