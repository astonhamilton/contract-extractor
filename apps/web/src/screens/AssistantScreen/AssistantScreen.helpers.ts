import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";

export function eventLabel(message: AssistantMessage): string {
  if (message.kind === "reasoning") {
    return "Reasoning";
  }
  if (message.kind === "tool_call") {
    return "Tool call";
  }
  if (message.kind === "tool_result") {
    return "Tool result";
  }
  if (message.kind === "hosted_tool_event") {
    return "Hosted tool";
  }
  return message.title;
}

export function isHostedWebSearchEvent(message: AssistantMessage): boolean {
  return (
    message.kind === "hosted_tool_event" &&
    (message.rawItem?.record.name === "web_search_call" ||
      message.rawItem?.record.provider_item_type === "web_search_call")
  );
}

export function isImageGenerationEvent(message: AssistantMessage): boolean {
  return (
    message.kind === "hosted_tool_event" &&
    (message.rawItem?.record.name === "image_generation_call" ||
      message.rawItem?.record.provider_item_type === "image_generation_call")
  );
}

export function imageGenerationPayload(
  message: AssistantMessage,
): Record<string, unknown> | null {
  const payload = message.rawItem?.record.provider_payload;
  return payload && typeof payload === "object" ? payload : null;
}

export function imageGenerationDataUrl(message: AssistantMessage): string | null {
  const payload = imageGenerationPayload(message);
  const result = payload?.result;
  const format = payload?.output_format;
  if (typeof result !== "string" || !result.trim()) {
    return null;
  }
  const mime = typeof format === "string" && format ? `image/${format}` : "image/png";
  return `data:${mime};base64,${result}`;
}

function formatToolArgumentValue(value: unknown): string {
  if (value == null) {
    return "null";
  }
  if (typeof value === "string") {
    return value;
  }
  if (
    typeof value === "number" ||
    typeof value === "boolean" ||
    typeof value === "bigint"
  ) {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => formatToolArgumentValue(item)).join(",");
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function toolCallArgumentSummary(message: AssistantMessage): string {
  const rawArguments = message.rawItem?.record.arguments;
  if (!rawArguments || typeof rawArguments !== "object") {
    return "";
  }
  const entries = Object.entries(rawArguments);
  if (entries.length === 0) {
    return "";
  }
  return entries
    .map(([key, value]) => `${key}=${formatToolArgumentValue(value)}`)
    .join(", ");
}

export function hostedWebSearchQuery(message: AssistantMessage): string {
  const action = message.rawItem?.record.provider_payload.action;
  if (action && typeof action === "object") {
    const query = (action as Record<string, unknown>).query;
    if (typeof query === "string" && query.trim()) {
      return query.trim();
    }
  }
  return message.content;
}

export function hostedWebSearchResultCount(message: AssistantMessage): number {
  const results = message.rawItem?.record.provider_payload.results;
  return Array.isArray(results) ? results.length : 0;
}

export function hostedWebSearchDomainSummary(message: AssistantMessage): string {
  const action = message.rawItem?.record.provider_payload.action;
  const sources =
    action && typeof action === "object"
      ? (action as Record<string, unknown>).sources
      : null;
  if (!Array.isArray(sources)) {
    return "";
  }

  const domains = new Set<string>();
  for (const source of sources) {
    if (!source || typeof source !== "object") {
      continue;
    }
    const url = (source as Record<string, unknown>).url;
    if (typeof url !== "string") {
      continue;
    }
    try {
      const hostname = new URL(url).hostname.replace(/^www\./, "");
      if (hostname) {
        domains.add(hostname);
      }
    } catch {
      continue;
    }
  }

  const orderedDomains = [...domains];
  if (orderedDomains.length === 0) {
    return "";
  }
  const visible = orderedDomains.slice(0, 3);
  const remainder = orderedDomains.length - visible.length;
  return remainder > 0
    ? `${visible.join(", ")} +${remainder}`
    : visible.join(", ");
}

