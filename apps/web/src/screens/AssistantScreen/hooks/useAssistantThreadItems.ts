import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type {
  AssistantMessage,
  AssistantThread,
  AssistantTurn,
} from "@/screens/AssistantScreen/AssistantScreen.types";
import {
  isTurnInProgress,
  mergeThreadItems,
} from "@/screens/AssistantScreen/AssistantScreen.threadState";
import { assistantQueries } from "@/services/assistant/assistantQueries";

export type AssistantThreadItemsState = {
  activeTurn: AssistantTurn | null;
  error: string | null;
  isRefreshing: boolean;
  isWorking: boolean;
  messages: AssistantMessage[];
  refreshThread: () => Promise<void>;
  status: "empty" | "loading" | "error" | "ready";
};

type AssistantThreadItemsOptions = {
  refreshThreads: () => Promise<void>;
  selectedThread: AssistantThread | null;
  updateThread: (
    threadId: string,
    updater: (thread: AssistantThread) => AssistantThread,
  ) => void;
};

export function useAssistantThreadItems({
  refreshThreads,
  selectedThread,
  updateThread,
}: AssistantThreadItemsOptions): AssistantThreadItemsState {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const backendThreadId = selectedThread?.backendThreadId ?? "";
  const itemsQuery = useQuery({
    ...assistantQueries.threadItems(backendThreadId),
    enabled: backendThreadId.length > 0,
    refetchInterval:
      selectedThread?.status === "streaming" || selectedThread?.status === "queued"
        ? 1000
        : false,
  });
  const activeTurn = itemsQuery.data?.active_turn ?? null;

  useEffect(() => {
    if (!selectedThread || !itemsQuery.data) {
      return;
    }
    updateThread(selectedThread.id, (current) =>
      mergeThreadItems(current, itemsQuery.data),
    );
  }, [itemsQuery.data, selectedThread?.id, updateThread]);

  async function refreshThread(): Promise<void> {
    if (isRefreshing) {
      return;
    }
    setIsRefreshing(true);
    try {
      if (backendThreadId) {
        await itemsQuery.refetch();
      }
      await refreshThreads();
    } finally {
      setIsRefreshing(false);
    }
  }

  const status =
    selectedThread === null
      ? "empty"
      : itemsQuery.isPending && backendThreadId
        ? "loading"
        : itemsQuery.isError
          ? "error"
          : "ready";
  const error =
    itemsQuery.error instanceof Error
      ? itemsQuery.error.message
      : itemsQuery.isError
        ? "Thread could not be loaded."
        : null;
  const messages = selectedThread?.messages ?? [];

  return {
    activeTurn,
    error,
    isRefreshing,
    isWorking:
      isTurnInProgress(activeTurn) ||
      selectedThread?.status === "streaming" ||
      selectedThread?.status === "queued" ||
      selectedThread?.status === "retrieving",
    messages,
    refreshThread,
    status,
  };
}
