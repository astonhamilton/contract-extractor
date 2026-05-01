import {
  assistantMessageFromApiItem,
  assistantThreadFromDetailApi,
  sortedAssistantMessages,
} from "@/screens/AssistantScreen/AssistantScreen.adapters";
import type {
  AssistantMessage,
  AssistantThread,
  AssistantTurn,
} from "@/screens/AssistantScreen/AssistantScreen.types";
import type {
  AssistantThreadItemsApiResponse,
} from "@/services/assistant/assistantApi";

export function isTurnInProgress(activeTurn: AssistantTurn | null): boolean {
  return activeTurn !== null;
}

function sameMessages(
  left: AssistantMessage[],
  right: AssistantMessage[],
): boolean {
  return (
    left.length === right.length &&
    left.every((message, index) => {
      const other = right[index];
      return (
        other !== undefined &&
        message.id === other.id &&
        message.seq === other.seq &&
        message.kind === other.kind &&
        message.role === other.role &&
        message.content === other.content
      );
    })
  );
}

function sameThread(left: AssistantThread, right: AssistantThread): boolean {
  return (
    left.id === right.id &&
    left.backendThreadId === right.backendThreadId &&
    left.title === right.title &&
    left.summary === right.summary &&
    left.status === right.status &&
    left.updatedAt === right.updatedAt &&
    left.itemsLoaded === right.itemsLoaded &&
    sameMessages(left.messages, right.messages)
  );
}

export function messagesFromThreadItems(
  response: AssistantThreadItemsApiResponse,
): AssistantMessage[] {
  return sortedAssistantMessages(
    response.items.map(assistantMessageFromApiItem),
  );
}

export function mergeThreadItems(
  current: AssistantThread,
  response: AssistantThreadItemsApiResponse,
): AssistantThread {
  const detailThread = assistantThreadFromDetailApi(response.thread, current);
  const next: AssistantThread = {
    ...detailThread,
    status: isTurnInProgress(response.active_turn)
      ? "streaming"
      : detailThread.status,
    messages: messagesFromThreadItems(response),
    itemsLoaded: true,
  };
  return sameThread(current, next) ? current : next;
}

export function mergeThreadSummaries(
  current: AssistantThread[],
  summaries: AssistantThread[],
): AssistantThread[] {
  return summaries.map((summary) => {
    const existing = current.find((thread) => thread.id === summary.id);
    if (!existing) {
      return summary;
    }
    return {
      ...summary,
      messages: existing.messages,
      itemsLoaded: existing.itemsLoaded,
    };
  });
}
